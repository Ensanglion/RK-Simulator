# Quick debug runner for a single attack from game.py
from classes import make_attack_for_debug

# Choose which attack to debug here:
ATTACK_NAME = 'Final' 

if __name__ == '__main__':
    attack = make_attack_for_debug(ATTACK_NAME)
    attack.run()