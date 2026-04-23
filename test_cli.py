from mininet.cli import CLI
from mininet.net import Mininet
net = Mininet()
CLI(net, script="/dev/null")
