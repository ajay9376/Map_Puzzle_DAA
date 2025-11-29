class Graph:
    def __init__(self):
        self.adj = {}

    def add_region(self, region):
        if region not in self.adj:
            self.adj[region] = []

    def add_border(self, r1, r2):
        self.add_region(r1)
        self.add_region(r2)
        self.adj[r1].append(r2)
        self.adj[r2].append(r1)

    def display(self):
        for region in self.adj:
            print(region, "->", self.adj[region])
