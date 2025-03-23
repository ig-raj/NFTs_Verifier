known_scammers = set()

def add_scammer(address):
    known_scammers.add(address)

def get_known_scammers():
    return known_scammers
