from time import sleep
from pysnmp import hlapi
from numpy import array, amin
from threading import Thread

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.revent import EventHalt
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet

log = core.getLogger("f.t_p")

############## Globals #############

virtual_ip = IPAddr("192.168.100.222")
virtual_mac = EthAddr("00:50:00:00:0d:00")

servers = {"192.168.100.248": "00:50:00:00:06:00", 
           "192.168.100.247": "00:50:00:00:07:00"}

ip_decision = None

################ Handlers ###################

def snmp_thread_func():
    global ip_decision
    
    server_list = ['192.168.100.247', '192.168.100.248']

    # ===========================================================================
    # oid_dict = {'cpu': '1.3.6.1.2.1.25.3.3.1.2.196608',
    #             'io_read': '1.3.6.1.4.1.2021.13.15.1.1.5.9',
    #             'io_write': '1.3.6.1.4.1.2021.13.15.1.1.6.9',
    #             'download': '1.3.6.1.2.1.2.2.1.10.2',
    #             'upload': '1.3.6.1.2.1.2.2.1.16.2'}
    # ===========================================================================

    oid_list = ['1.3.6.1.2.1.25.3.3.1.2.196608',
                '1.3.6.1.4.1.2021.13.15.1.1.5.9',
                '1.3.6.1.4.1.2021.13.15.1.1.6.9',
                '1.3.6.1.2.1.2.2.1.10.2',
                '1.3.6.1.2.1.2.2.1.16.2']

    weight_coefs = [0, 0, 0, 0, 1]

    snmp_objects = list()
    for server in server_list:
        snmp_objects.append(SNMPGetter(server, oid_list))

    while True:
        metrics = dict()
        for server in snmp_objects:
            snmp_results = server.get()
            if len(snmp_results) == len(oid_list):
                metrics[server.target] = list()
                for item in oid_list:
                    metrics[server.target].append(snmp_results[item])
            else:
                continue

        ip_list = list()
        oid_values_list = list()
        for ip, oid_values in metrics.iteritems():
            ip_list.append(ip)
            oid_values_list.append(oid_values)

 
        a_array = array(oid_values_list)
        minimums = amin(a_array, axis=0).tolist()
        b = [[weight_coefs[i] if parameters[i] == minimums[i] else 0 for i in range(5)] for parameters in oid_values_list]
        print b
        score = [sum(candidate) for candidate in b]
        winner_index = score.index(max(score))
        ip_decision = ip_list[winner_index]
        print "Decision: " + ip_decision
        sleep(1)


class SNMPGetter(object):
#    def __init__(self, target, oids_list, credentials='public', port=161, count=1, start_from=0):
    def __init__(self, target, oids_list, credentials='public', port=1024, count=1, start_from=0):
        self.target = target
        self.oids_list = oids_list
        self.credentials = hlapi.CommunityData(credentials)
        self.port = port
        self.engine = hlapi.SnmpEngine()
        self.context = hlapi.ContextData()

        # count and start_from are used only for get_bulk()
        self.count = count
        self.start_from = start_from

        self.object_types = list()
        for oid in self.oids_list:
            self.object_types.append(hlapi.ObjectType(hlapi.ObjectIdentity(oid)))

    def cast(self, value):
        try:
            return int(value)
        except (ValueError, TypeError):
            try:
                return float(value)
            except (ValueError, TypeError):
                try:
                    return str(value)
                except (ValueError, TypeError):
                    pass
        return value

    def fetch(self, handler, count):
        result = list()
        for i in range(count):
            try:
                error_indication, error_status, error_index, var_binds = next(handler)
                if not error_indication and not error_status:
                    items = dict()
                    for var_bind in var_binds:
                        items[str(var_bind[0])] = self.cast(var_bind[1])
                    result.append(items)
                else:
                    raise RuntimeError('Got SNMP error: {0}'.format(error_indication))
            except StopIteration:
                break
        return result

    def get(self):
        get_handler = hlapi.getCmd(
            self.engine,
            self.credentials,
            hlapi.UdpTransportTarget((self.target, self.port),timeout=10.0),
            self.context,
            *self.object_types
        )
        return self.fetch(get_handler, 1)[0]

    def get_bulk(self):
        get_bulk_handler = hlapi.bulkCmd(
            self.engine,
            self.credentials,
            hlapi.UdpTransportTarget((self.target, self.port),timeout=10.0),
            self.context,
            self.start_from, self.count,
            *self.object_types
        )
        return self.fetch(get_bulk_handler, self.count)


class Switch(object):
    def __init__(self, connection):
        self.connection = connection
        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        global ip_decision
        print "entering PacketIn function"
        packet = event.parsed

        # ARP handling
        if packet.type == 0x0806:
            if packet.payload.opcode == arp.REQUEST:
                if packet.payload.protodst == virtual_ip:
                    print "handling ARP request for vIP"

                    # form a reply packet
                    arp_reply = arp()
                    arp_reply.hwsrc = virtual_mac
                    arp_reply.hwdst = packet.src
                    arp_reply.opcode = arp.REPLY
                    arp_reply.protosrc = virtual_ip
                    arp_reply.protodst = packet.payload.protosrc
                    ether = ethernet()
                    ether.type = ethernet.ARP_TYPE
                    ether.dst = packet.src
                    ether.src = virtual_mac
                    ether.payload = arp_reply

                    # send this packet to the switch
                    packet_out = of.ofp_packet_out()
                    packet_out.data = ether.pack()
                    packet_out.actions.append(of.ofp_action_output(port = of.OFPP_TABLE))
                    event.connection.send(packet_out)

        # Handle traffic destined to virtual IP
        if packet.type == 0x0800:
            if packet.payload.dstip == virtual_ip:

                # SNMP selection of servers
                print "selected server: " + str(ip_decision)
                selected_server_ip = IPAddr(ip_decision)
                selected_server_mac = EthAddr(servers[ip_decision])

                # preparing packet for server
                print "instruction: send packet from client to server"
                msg = of.ofp_flow_mod()
                msg.priority = 1500
                msg.match = of.ofp_match()
                msg.match.dl_type = 0x0800
                msg.match.nw_proto = 6
                msg.match.nw_dst = virtual_ip
                msg.match.nw_src = packet.payload.srcip
                msg.match.tp_src = packet.payload.payload.srcport
                msg.actions.append(of.ofp_action_dl_addr(of.OFPAT_SET_DL_DST, selected_server_mac))
                msg.actions.append(of.ofp_action_nw_addr(of.OFPAT_SET_NW_DST, selected_server_ip))
                msg.actions.append(of.ofp_action_output(port = of.OFPP_NORMAL))
                event.connection.send(msg)

                # preparing packet for client
                print "instruction: send packet from server to client"
                rev_msg = of.ofp_flow_mod()
                rev_msg.priority = 1500
                rev_msg.match = of.ofp_match()
                rev_msg.match.dl_type = 0x0800
                rev_msg.match.nw_proto = 6
                rev_msg.match.nw_src = selected_server_ip
                rev_msg.match.nw_dst = msg.match.nw_src
                rev_msg.match.tp_dst = msg.match.tp_src
                rev_msg.actions.append(of.ofp_action_dl_addr(of.OFPAT_SET_DL_SRC, virtual_mac))
                rev_msg.actions.append(of.ofp_action_nw_addr(of.OFPAT_SET_NW_SRC, virtual_ip))
                rev_msg.actions.append(of.ofp_action_output(port = of.OFPP_NORMAL))
                event.connection.send(rev_msg)

        return EventHalt


class proactive_flow(object):
    def __init__ (self):
        self.log = log.getChild("Unknown")
        core.listen_to_dependencies(self, listen_args={'openflow':{'priority':0}})

    def _handle_openflow_ConnectionUp(self, event):
        if event.connection is None:
            self.log.debug("can't send table: disconnected")
            return
        print "starting snmp loop and sending proactive flows to switch"
        
        # start SNMP thread
        t = Thread(target=snmp_thread_func)
        t.daemon = True
        t.start()

        # clear previous flows entries if any
        clear = of.ofp_flow_mod(command=of.OFPFC_DELETE)
        event.connection.send(clear)
        event.connection.send(of.ofp_barrier_request())

        # ARP -> PacketIn, Normal, Controller
        arp_rule = of.ofp_flow_mod()
        arp_rule.match = of.ofp_match()
        arp_rule.match.dl_type = 0x0806
        arp_rule.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
        arp_rule.actions.append(of.ofp_action_output(port = of.OFPP_NORMAL))
        event.connection.send(arp_rule)

        # DstIP: vIP -> PacketIn, PRI: 1000
        vip_rule = of.ofp_flow_mod()
        vip_rule.match = of.ofp_match()
        vip_rule.match.dl_type = 0x0800
        vip_rule.match.nw_dst = virtual_ip
        vip_rule.priority = 1000
        vip_rule.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
        event.connection.send(vip_rule)

        # Any -> Normal, PRI: 1001
        any_rule = of.ofp_flow_mod()
        any_rule.priority = 500
        any_rule.actions.append(of.ofp_action_output(port = of.OFPP_NORMAL))
        event.connection.send(any_rule)

        # initialize Switch() instance
        Switch(event.connection)
        

def launch():
    core.registerNew(proactive_flow)

