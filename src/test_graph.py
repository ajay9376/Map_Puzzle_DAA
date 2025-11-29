from graph import Graph

g = Graph()
g.add_border('A', 'B')
g.add_border('A', 'C')
g.add_border('B', 'D')
g.add_border('C', 'D')

g.display()
