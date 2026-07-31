class DictDefn:

    def __init__(self, defn_id, st, defn):
        self.id = defn_id
        self.term = st
        self.defn = defn

    def serialize_defn(self) -> str:
        return str(self.defn)

    @classmethod
    def deserialize_defn(cls, raw: str):
        return raw

    def __str__(self):
        return str((self.id, self.term, str(self.defn)))

    def __repr__(self):
        return self.__str__()

    def to_tsv(self):
        return f"{self.id}\t{self.term}\t{self.serialize_defn()}"

    def __lt__(self, other):
        return self.id < other.id
