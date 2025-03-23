from db import known_scammers

def check_scammer(address):
    return address in known_scammers
