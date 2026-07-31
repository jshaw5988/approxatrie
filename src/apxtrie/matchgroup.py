class MatchGroup:

    def __init__(self, start, end, edist_left, edist_cost, defn):
        self.start = start
        self.end = end
        self.edist_left = edist_left
        self.edist_cost = edist_cost
        self.defn = defn

    def __str__(self):
        atuple = ("start=%s",
                  "end=%s",
                  "edist_left=%d",
                  "edist_cost=%d",
                  "defn=%s")
        return str(atuple)
