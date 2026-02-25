from html.parser import HTMLParser

class JournalParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.tr_attrs = []
        self.current_row = []
        self.in_td = False
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            attr_dict = dict(attrs)
            if attr_dict.get("class") == "item":
                self.in_tr = True
                self.tr_attrs = attrs
                self.current_row = []
        elif tag == "td" and self.in_tr:
            self.in_td = True
            self.current_cell_data = []

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_tr:
            self.in_tr = False
            self.rows.append({"attrs": self.tr_attrs, "data": self.current_row})
        elif tag == "td" and self.in_tr:
            self.in_td = False
            self.current_row.append(" ".join(self.current_cell_data).strip())

    def handle_data(self, data):
        if self.in_td:
            self.current_cell_data.append(data.strip())

parser = JournalParser()
with open("c:/Users/User/Desktop/MineTrack/backend/esmo_journal.html", "r", encoding="utf-8") as f:
    parser.feed(f.read())

for row in parser.rows[:5]:
    print(f"Attributes: {row['attrs']}")
    print(f"Data: {row['data']}")
    print("-" * 20)
