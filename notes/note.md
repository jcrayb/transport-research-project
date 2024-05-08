OSMNX:

experimented a little bit with osmnx. So, nodes have an int ID, and edges have 2 ints, corresponding to which node they connect.

Using indexes on the city object, can fetch info on nodes using City[node_idx] and on an edge using City[node1_idx][node2_idx].

So next step would be to find how to reverse this process, so we can assign which nodes have cameras and which don't based on GPS coordinates or address maybe? We could find a node based on which streets it connects to but that would mean looping through every node in the city.
