from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.revent import EventHalt
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet

log = core.getLogger("f.t_p")

############## Global constants #############

virtual_ip = IPAddr("192.168.100.222")
virtual_mac = EthAddr("00:50:00:00:0d:00")

server = {}
server[0] = {'ip':IPAddr("192.168.100.248"), 'mac':EthAddr("00:50:00:00:06:00")}
server[1] = {'ip':IPAddr("192.168.100.247"), 'mac':EthAddr("00:50:00:00:07:00")}
total_servers = len(server)

server_index = 0

################ Handlers ###################

class Switch(object):
    def __init__(self, connection):
        self.connection = connection
        connection.addListeners(self)

    def _handle_PacketIn(self, event):
        print "entering PacketIn function"
        global server_index
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

                # Round Robin selection of servers
                index = server_index % total_servers
                print "selected server: " + str(index)
                selected_server_ip = server[index]['ip']
                selected_server_mac = server[index]['mac']
                server_index += 1

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
        print "sending proactive flows to switch"

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

