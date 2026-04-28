import random
import os
import cards_ascii
from cards_ascii import colors
import time
import instant_input
import ast

"""
###############
##### MISC #####
###############
"""

# Get random seed
seed = random.randrange(os.sys.maxsize)
random.seed(seed)

"""
###################
 #### CONFIG FILE ####
###################
"""

CONFIG_FILE = "game_configs.txt"

default_configs = {
	"instant_actions": False
}

configs = default_configs.copy()

def load_configs():
	global configs
	if not os.path.exists(CONFIG_FILE):
		save_configs()
		return
	
	with open(CONFIG_FILE, "r") as f:
		for line in f:
			if "=" in line:
				key, value = line.strip().split("=", 1)
				if key in configs:
					configs[key] = value.lower() == "true"

def save_configs():
	with open(CONFIG_FILE, "w") as f:
		for k, v in configs.items():
			f.write(f"{k}={'true' if v else 'false'}\n")

load_configs()

"""
###############
### FUNCTIONS ###
###############
"""

def get_input(text, type, error="Invalid input!"):
	# Check if instant input is on
	if not configs["instant_actions"]:
		while True:
			try:
				var = input(text)
				return type(var)
			except Exception:
				print(error)
	else:
		print(text, end="", flush=True)
		with instant_input.InstantInput() as inp:
			while True:
				key = inp.get_key()
				return type(key)


def clean():
	os.system("cls" if os.name == "nt" else "clear")

def strike(text):
    result = ''
    for c in text:
        result = result + c + '\u0336'
    return result

SAVE_STATE_FILE = "save_state.txt"

save_state_vars = ["current_room", "difficulty", "room.card_seq", "room.deck", "seed", "first_game_action", "player.last_card_killed", "player.current_weapon", "room.skipped_last", "room.played_first_card", "rng_state_at_room_start"]

def save_state(vars, save_file):
    with open(save_file, "w") as f:
    	for k in vars:
    		if "." in k:
    			obj_name, attr = k.split(".", 1)
    			value = getattr(globals()[obj_name], attr)
    		else:
    			value = globals()[k]
    		f.write(f"{k}={value}\n")

def load_state(save_file):
	global room
	import ast
	
	# First pass: just collect all values
	values = {}
	with open(save_file, "r") as f:
		for line in f:
			if "=" not in line:
				continue
			k, v = line.strip().split("=", 1)
			try:
				values[k] = ast.literal_eval(v)
			except (ValueError, SyntaxError):
				values[k] = v
	
	# Restore RNG first, before anything touches random
	if "rng_state_at_room_start" in values:
		random.setstate(values["rng_state_at_room_start"])
	
	# Now apply all values
	for k, v in values.items():
		if k == "rng_state":
			continue
		if "." in k:
			obj_name, attr = k.split(".", 1)
			setattr(globals()[obj_name], attr, v)
		else:
			globals()[k] = v
"""
###########
### DECK ###
###########
"""
card_values = {
	"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
	"8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14
}

values_to_cards =  {
	2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
	8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A"
}

card_names = list(card_values.keys())
suits = ["spades", "diamonds", "hearts", "clubs", "bananas"]

class Card:
	def __init__(self, rank, suit):
		self.rank = rank
		self.suit = suit

	def strength(self):
		return card_values[self.rank]

	def full(self):
		return f"{self.rank} of {self.suit}"
	
	def get_suit(self):
		return self.suit

deck = {}
deck_names = []

for s in suits:
	for r in card_names:
		name = f"{r}_of_{s}"
		deck[name] = Card(r, s)
		deck_names.append(name)

deck_in_ascii = cards_ascii.cards_name_to_ascii

"""
################
### ROOM LOGIC ###
################
"""

class Room:
	def __init__(self, deck: list, blank=False):
		self.original_deck = deck.copy()  # Never modified - used for endless mode
		self.deck = deck.copy()  # Cards not yet dealt
		
		self.heal_used = False
		self.skipped_last = False
		self.played_first_card = False
		
		if not blank:
			# Deal the 4 initial cards
			self.card_seq = random.sample(self.deck, k=4)
			# Remove 'em from the deck
			for card in self.card_seq:
				self.deck.remove(card)
	
	def choose_card(self, card):
		card_selected = self.card_seq[card-1]
		self.card_seq.remove(card_selected)
		return card_selected
	
	def add_cards(self, amount):
		amount = min(amount, len(self.deck))
		if amount > 0:
			cards_to_add = random.sample(self.deck, k=amount)
			for c in cards_to_add:
				self.card_seq.append(c)
				self.deck.remove(c)
	
	def reset(self, amount):
		# Return current cards to deck
		self.deck.extend(self.card_seq)
		self.card_seq = []
		# Deal new cards
		self.add_cards(min(amount, len(self.deck)))
	
	def replenish_deck(self):
		# Restore full deck and deal new cards
		self.deck = self.original_deck.copy()
		self.card_seq = []
		self.add_cards(4)


class Player:
	def __init__(self, max_hp):
		self.max_hp = max_hp
		self.hp = max_hp
		self.current_weapon = 0
		self.last_card_killed = 0
	
	def take_damage(self, amount):
		self.hp -= amount
	
	def get_HP(self):
		return self.hp
	
	def heal(self, amount):
		if amount + self.hp > self.max_hp:
			self.hp = self.max_hp
		else:
			self.hp += amount

player = Player(20)
current_room = 1

# Open and load save files for high score
#easy_save_file = "easy_save_file.txt"

#if os.path.exists(easy_save_file) != True:
#	with open(easy_save_file, "w") as f:
#		f.write(" ")

#easy_high_score = 0
#with open(easy_save_file, "r") as f:
#	easy_high_score = f.read()

#normal_save_file = "normal_save_file.txt"

#if os.path.exists(normal_save_file) != True:
#	with open(normal_save_file, "w") as f:
#		f.write(" ")

#normal_high_score = 0
#with open(normal_save_file, "r") as f:
#	normal_high_score = f.read()

"""
###################
#### SAVE FILE ####
###################
"""

SAVE_FILE = "scoundrel_saves.txt"

default_saves = {
    "easy_high_score": 0,
    "normal_high_score": 0
}

saves = default_saves.copy()

def load_saves():
    global saves
    if not os.path.exists(SAVE_FILE):
        save_data()
        return
    
    with open(SAVE_FILE, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                if key in saves:
                    # Try to convert to int, otherwise keep as string
                    try:
                        saves[key] = int(value)
                    except ValueError:
                        saves[key] = value

def save_data():
    with open(SAVE_FILE, "w") as f:
        for k, v in saves.items():
            f.write(f"{k}={v}\n")

load_saves()

# Game states
game_over = False
past_menu = False
can_die = True
infinite_skips = False
use_weapon = True
difficulty = "easy"
endless_mode = False
first_game_action = True
rng_state_at_room_start = random.getstate()

# Run info
highest_weapon = 0
highest_card_killed = 0
highest_damage = 0
highest_heal = 0
start_time = 0

game_tutorial1 = f"""
Rooms

The Room: Each room consists of 4 cards dealt from the deck.

Advancing: Once you have interacted with 3 out of the 4 cards in a room, you move on to the next room.

Card Types and Effects

letter values:
A - 14
K - 13
Q - 12
J - 11
T - 10

{colors.yellow}Clubs{colors.end} and {colors.dark_blue}Spades{colors.end} (Enemies): These represent monsters that deal damage equal to their rank. 2 is the weakest, and Aces are the strongest.

{colors.red}Hearts{colors.end} (Healing): These cards restore your health based on their rank. You may only heal once per room. If you interact with additional Heart cards in the same room, the extra healing is discarded.

{colors.green}Diamonds{colors.end} (Weapons): These grant you attack power based on their rank. You can use a weapon to defeat enemies, but there is a restriction: once you slay a monster, you can only use that weapon again on a monster with a lower rank than the one you just killed. If you attack a monster stronger than the last one you killed with that weapon, you take full damage.
"""

game_tutorial2 = f"""
Actions

Interact with Card:
{colors.yellow}Ene{colors.end}{colors.dark_blue}mies{colors.end}: If you have no weapon, you take full damage. If you have a weapon, the weapon rule applies.

{colors.red}Hearts{colors.end}: Heals you (subject to the once per room limit).

{colors.green}Diamonds{colors.end}: Picking up a Diamond equips it as your weapon. If you select a weapon weaker than your current one without using the Change Weapon action, it is discarded.

Change Weapon: This allows you to replace your current weapon with a Diamond card currently in the room, whether it is stronger or weaker.

Skip Room: You may skip the current room and move to the next one, provided that you did not skip the previous room and you have not interacted with any cards in the current room yet.

Difficulties

Easy mode has the standard 52 cards, having high diamonds and hearts (from J - A).

Normal mode has 44 cards, not having the high diamonds and hearts.

Endless mode is unlocked after beating a difficulty. If beaten in easy difficulty, endless mode will continue being in easy mode, and so with normal mode.
"""

game_tutorial3 = """
Controls

By default, actions require pressing ENTER.
You can enable "Instant Actions" in the Configs menu.

When Instant Actions are ON, menus react instantly to key presses.
"""

tutorial_deck = ["A_of_diamonds", "2_of_spades", "5_of_clubs", "3_of_hearts"]

def tutorial():
	tutorial_over = False
	tutorial_part = 1
	tutorial_explanation = "rooms"
	tutorial_room = Room(tutorial_deck)
	tutorial_player = Player(20)
	
	print("Hello! This is SlimeStaff484, and this is my game: Scoundrel!\n")
	input("Press enter to continue...")
	clean()
	print("If you chose to do this tutorial, prolly means your attention span does not exist :D\n")
	input("Press enter to continue...")
	clean()
	print("In any case, let's get to business :)\n")
	input("Press enter to continue...")
	clean()
	
	print("This is a room:\n")
	while not tutorial_over:
		# Room explanation
		if tutorial_explanation == "rooms":
			print("==========\\ ROOM /==========")
			cards_ascii.print_cards_side_by_side([deck_in_ascii[name] for name in tutorial_room.card_seq])
			if tutorial_part == 1:
				print("\nAs you can see, it consists of 4 cards.\n")
				tutorial_part = 2
				input("Press enter to continue...")
				clean()
				continue
			if tutorial_part == 2:
				print("\nNow, you see those 4 cards, right?\nTheir suits are what define them.\n")
				tutorial_part = 3
				input("Press enter to continue...")
				clean()
				continue
			if tutorial_part == 3:
				# Cards explanation
				diamonds_pos = tutorial_room.card_seq.index("A_of_diamonds") + 1
				hearts_pos = tutorial_room.card_seq.index("3_of_hearts") + 1
				spades_pos = tutorial_room.card_seq.index("2_of_spades") + 1
				clubs_pos = tutorial_room.card_seq.index("5_of_clubs") + 1
				
				index_padding = {1: 0, 2: 18, 3: 28, 4: 38}
				name_to_index = {"hearts": hearts_pos, "spades": spades_pos, "diamonds": diamonds_pos, "clubs": clubs_pos}
				
				st = "________"
				i = name_to_index['diamonds']
				p = index_padding[i]
				print(f"{st:>{p}}")
				
				print("\nThis is a diamond card; it acts as your weapon, and it'll give you strength based on their number.\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 4
				continue
			
			if tutorial_part == 4:
				i = name_to_index['hearts']
				p = index_padding[i]
				print(f"{st:>{p}}")
				
				print("\nThis is a heart card; it'll heal you based on their number.\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 5
				continue
			
			if tutorial_part == 5:
				index_padding = {1: 0, 2: 10, 3: 20, 4: 30}
				i1 = name_to_index['clubs']
				i2 = name_to_index['spades']
				p1 = index_padding[i1]
				p2 = index_padding[i2]
				p1, p2 = sorted([p1, p2])
				a = [" " * p1, st, " " * (p2 - p1 - len(st)), st]
				print(''.join(a))
				
				print("\nThose are the enemies, clubs and spades; they deal damage based on their number\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 6
			
			if tutorial_part == 6:
				# Player introduction
				print("See? It's not that difficult, right?\n")
				input("Press enter to continue...")
				clean()
				print("Lemme now explain the player stats.\n")
				input("Press enter to continue...")
				clean()
				tutorial_explanation = "player"
				tutorial_part = 1
			
		if tutorial_explanation == "player":
			print("\n==========\\ YOU /==========\n")
			print(f"HP: {tutorial_player.hp}")
			print(f"Current strenght: {tutorial_player.current_weapon}")
			print(f"Last card killed: {tutorial_player.last_card_killed}")
			print(f"Cards left: {len(tutorial_room.deck)}")
			
			if tutorial_part == 1:
				print("\nThis is all your information!\n")
				input("Press enter to continue...")
				clean()
				print("...\n")
				input("Press enter to continue...")
				clean()
				print("What? You want me to explain it???\n")
				input("Press enter to say yes...")
				clean()
				print("*Sigh* Fine, lemme explain it")
				input("Press enter to continue...")
				clean()
				tutorial_part = 2
			
			if tutorial_part == 2:
				print("\n==========\\ YOU /==========\n")
				print(f"HP: {tutorial_player.hp} <- This is your HP. If it reaches 0, you lose.\n")
				input("Press enter to continue")
				clean()
				tutorial_part = 3
			
			if tutorial_part == 3:
				print("\n==========\\ YOU /==========\n")
				print(f"HP: {tutorial_player.hp}")
				print(f"Current strenght: {tutorial_player.current_weapon} <- This is your current strenght. Pretty much your defense.\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 4
			
			if tutorial_part == 4:
				print("\n==========\\ YOU /==========\n")
				print(f"HP: {tutorial_player.hp}")
				print(f"Current strenght: {tutorial_player.current_weapon}")
				print(f"Last card killed: {tutorial_player.last_card_killed} <- This is the last card you killed. This info is very important, and will be explained soon.\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 5
			
			if tutorial_part == 5:
				print("\n==========\\ YOU /==========\n")
				print(f"HP: {tutorial_player.hp}")
				print(f"Current strenght: {tutorial_player.current_weapon}")
				print(f"Last card killed: {tutorial_player.last_card_killed}")
				print(f"Cards left: {len(tutorial_room.deck)} <- This is your win condition. If it reaches 0, you win the game.\n")
				input("Press enter to continue...")
				clean()
				print("That's it for the player info. Now lemme your actions.\n")
				input("Press enter to continue...")
				clean()
				tutorial_explanation = "actions"
				tutorial_part = 0
		
		if tutorial_explanation == "actions":
			print("\n==========\\ ACTIONS /==========\n")
			print("1 - Select card")

			print("2 - Skip")
			
			if tutorial_part == 0:
				clean()
				print("\n==========\\ ACTIONS /==========\n")
				print("1 - Select card <- This does what it says.\n")
				input("Press enter to continue...")
				clean()
				print("\n==========\\ ACTIONS /==========\n")
				print("1 - Select card")
				print("2 - Skip <- This allows you to skip a room if:\n")
				print("	You didn't skip the last room;")
				print("	You haven't made an action in the current room.")
				print("\nYou can use it again if you beat the room you got after skipping.\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 1
				continue
		
			if tutorial_part == 1:
				print(f"\nAfter selecting 'select card', you'll chose between the current cards available on the room\nLike this:\nSelect the card (1 - {len(tutorial_room.card_seq)})")
				input("Press enter to continue...")
				clean()
				tutorial_part = 2
			if tutorial_part == 2:
				print("Now, I'll help you to see how the game works!")
				input("Press enter to continue...")
				clean()
				tutorial_explanation = "gameplay"
				tutorial_part = 0
		
		if tutorial_explanation == "gameplay":
			print("Room: " + str(current_room) + "     Difficulty: " + difficulty)
			print("==========\\ ROOM /==========")
			cards_ascii.print_cards_side_by_side([deck_in_ascii[name] for name in tutorial_room.card_seq])
			
			print("\n==========\\ YOU /==========\n")
			print(f"HP: {tutorial_player.hp}")
			print(f"Current strenght: {tutorial_player.current_weapon}")
			print(f"Last card killed: {tutorial_player.last_card_killed}")
			print(f"Cards left: {len(tutorial_room.deck)}")
			print("\n==========\\ ACTIONS /==========\n")
			print("1 - Select card")

			print("2 - Skip")
			if tutorial_part == 0:
				print("\nLet's start! Select the Ace of diamonds.\nSelect the 1st option:\n")
				player_input = get_input("#", str)
			
				while player_input != "1":
					player_input = get_input("\nThat ain't 1, is it?\n#", str)
			
				if player_input == "1":
					print(f"\nSelect the card (1 - {len(tutorial_room.card_seq)})\n")
					player_input = get_input("#", str)
					while player_input != str(diamonds_pos):
						player_input = get_input("\nThat ain't a diamond.\n#", str)
					if player_input == str(diamonds_pos):
						tutorial_player.current_weapon = 14
						tutorial_room.card_seq.remove("A_of_diamonds")
						if spades_pos > diamonds_pos and spades_pos != 1:
							spades_pos -= 1
						if clubs_pos > diamonds_pos and clubs_pos != 1:
							clubs_pos -= 1
						if hearts_pos > diamonds_pos and hearts_pos != 1:
							hearts_pos -= 1
						clean()
						print("You got 14 strength from the Ace! Btw, the letter cards have those values:\n	A - 14;\n	K - 13;\n	Q - 12;\n	J - 11;\n	T - 10;")
						input("Press enter to continue...")
						clean()
						tutorial_part = 1
						continue
			
			if tutorial_part == 1:
				print("\nCool, now kill the 2 of spades :)\n")
				player_input = get_input("#", str)
				
				while player_input != "1":
					player_input = get_input("\nDo you know how to count?\n#", str)
				
				if player_input == "1":
					print(f"\nSelect the card (1 - {len(tutorial_room.card_seq)})\n")
					player_input = get_input("#", str)
					while player_input != str(spades_pos):
						player_input = get_input("\nThat is no spades, my friend\n#", str)
			
				tutorial_player.last_card_killed = 2
				if clubs_pos > spades_pos and clubs_pos != 1:
					clubs_pos -= 1
				if hearts_pos > spades_pos and hearts_pos != 1:
					hearts_pos -= 1
				tutorial_room.card_seq.remove("2_of_spades")
				print("\nYou took 0 damage!\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 2
				continue
			
			if tutorial_part == 2:
				print("\nYou see that your last killed card is now 2? you can't kill anything above that with the weapon; so 2 being the weakest card means that the strongest weapon is now useless :)\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 3
				continue
			
			if tutorial_part == 3:
				print("\nDon't worry, the number resets after you switch weapons ;)\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 4
				continue
			
			if tutorial_part == 4:
				print("\nNow, kill the 5 of clubs real quick.\n")
				player_input = get_input("#", str)
				
				while player_input != "1":
					player_input = get_input("\nYou ain't selecting nothing with this\n#", str)
				
				if player_input == "1":
					print(f"\nSelect the card (1 - {len(tutorial_room.card_seq)})\n")
					player_input = get_input("# ", str)
					while player_input != str(clubs_pos):
						player_input = get_input("\nI'm running out of stuff to say\n#", str)
				
				tutorial_room.card_seq.remove("5_of_clubs")
				tutorial_player.take_damage(5)
				if hearts_pos > clubs_pos and hearts_pos != 1:
					hearts_pos -= 1
				print("\nYou took 5 damage!\n")
				input("Press enter to continue...")
				clean()
				print("Oh no, you took damage! D:\n")
				input("Press enter to continue...")
				clean()
				tutorial_part = 5
				continue
			
			if tutorial_part == 5:
				print("\nSelect the heart card! So you'll heal :)\n")
				player_input = get_input("# ", str)
				
				while player_input != "1":
					print("\n...")
					player_input = get_input("\n#", str)
				if player_input == "1":
					print(f"\nSelect the card (1 - {len(tutorial_room.card_seq)})\n")
					player_input = get_input("#", str)
					
					while player_input != str(hearts_pos):
						print("\n...\n")
						player_input = get_input("#", str)
					
					player.heal(3)
					tutorial_room.card_seq.remove("3_of_hearts")
					print("\nYou healed 3 HP!\n")
					input("Press enter to continue...")
					clean()
					tutorial_part = 0
					tutorial_explanation = "over"
		
		if tutorial_explanation == "over":
			print("And that's pretty much it!\n")
			input("Press enter to continue...")
			clean()
			print("You should be good to go. Hope you have a fun time playing :)\n")
			input("Press enter to continue...")
			clean()
			tutorial_over = True

"""
################
 ### GAME LOOP ###
################
"""
while not game_over or endless_mode:
	clean()
	while not past_menu:
		clean()
		print("""  ____                            _          _ 
 / ___|  ___ ___  _   _ _ __   __| |_ __ ___| |
 \___ \ / __/ _ \| | | | '_ \ / _` | '__/ _ \ |
  ___) | (_| (_) | |_| | | | | (_| | | |  __/ |
 |____/ \___\___/ \__,_|_| |_|\__,_|_|  \___|_|
 """)
		if saves["easy_high_score"] > 0:
		    print(f"\nEndless easy high score: {saves['easy_high_score']}\n")
		
		if saves["normal_high_score"] > 0:
		    print(f"Endless normal high score: {saves['normal_high_score']}\n")
		
		print("1 - Start game\n")
		print("2 - Tutorial\n")
		print("3 - Credits\n")
		print("4 - configurations\n")
		menu_options = get_input("Select an option to start:\n# ", str, "")
		while not menu_options.isnumeric():
			menu_options = get_input("\n#", str)
		
		menu_options = int(menu_options)
		
		while menu_options not in [1, 2, 3, 4]:
			menu_options = get_input("Invalid input!\n# ", str, "")
			while not menu_options.isnumeric():
				menu_options = get_input("\n# ", str)
			menu_options = int(menu_options)
		
		if menu_options == 1:
			clean()
			print("Select your difficulty:\n1 - Easy\n2 - Normal")
			
			an = get_input("# ", str)
			while not an.isnumeric():
				an = get_input("\n# ", str)
				
			an = int(an)
				
			while an not in [1, 2]:
				an = get_input("\n# ", str)
				while not an.isnumeric():
					an = get_input("\n# ", str)
				an = int(an)
			
			if an == 1:
				difficulty = "easy"
				#past_menu = True
			else:
				difficulty = "normal"
				#past_menu = True
			set_seed = input("\nSeed (leave empty if you want a radom seed)\n# ")
			
			if set_seed == "luckyseven":
				print("secret seed lol")
			
			if set_seed == "randombsgo":
				card_amt = 44 if difficulty == "normal" else 52
				
			if set_seed.isnumeric():
				random.seed(int(set_seed))
				past_menu = True
			else:
				past_menu = True
			
		if menu_options == 2:
			clean()
			print("What tutorial do you want to do?\n")
			an = get_input("1 - Text\n2 - Visual\n#", str)
			while an not in ["1", "2"]:
				an = get_input("#\n", str)
			if an == "1":
				clean()
				print(game_tutorial1)
				input("\nPress enter to continue...")
				clean()
				print(game_tutorial2)
				input("\nPress enter to continue...")
				clean()
				print(game_tutorial3)
				input("\nPress enter to continue...")
				clean()
			else:
				clean()
				tutorial()

		elif menu_options == 3:
			clean()
			print("Game made by SlimeStaff484!\n\nHope you enjoy!")
			input("\nPress enter to continue...")
			clean()
		if menu_options == 4:
			while True:
				clean()
				print("========== CONFIGS ==========\n")
				print(f"1 - Instant actions: {'ON' if configs['instant_actions'] else 'OFF'}")
				print(f"2 - Reset saves")
				print("3 - Back\n")
		
				an = get_input("# ", str)
				while not an.isnumeric():
					an = get_input("\n# ", str)
				
				an = int(an)
				
				while an not in [1, 2, 3]:
					an = get_input("\n# ", str)
					while not an.isnumeric():
						an = get_input("\n# ", str)
					an = int(an)
				
				if an == 1:
					configs["instant_actions"] = not configs["instant_actions"]
					save_configs()
				elif an == 2:
					sure = get_input("You sure?\n1 - yes\n2 - no\n#", str)

					while not sure.isnumeric():
						sure = get_input("\n# ", str)
					
					sure = int(sure)
					
					while sure not in [1, 2]:
						sure = get_input("\n# ", str)
						while not sure.isnumeric():
							sure = get_input("\n# ", str)
						sure = int(sure)
					
					if sure == 2:
						continue
					saves["easy_high_score"] = 0
					saves["normal_high_score"] = 0
					save_data()
				else:
					clean()
					break
	
	# Remove cards for normal difficulty
	if difficulty == "normal":
		for i in ["diamonds", "hearts"]:
			for j in range(11, 15):
				c_r = values_to_cards[j]
				c = f"{c_r}_of_{i}"
				if c in deck_names:
					deck_names.remove(c)
	
	if set_seed != "potassium":
		deck_names = [name for name in deck_names if name.split("_")[-1] != "bananas"]
	
	# Create room after difficulty is set
	# Just before room creation (~line 526)
	if 'room' not in locals():
		room = Room(deck_names.copy())
		rng_state_at_room_start = random.getstate()
		
	clean()
	print("Room: " + str(current_room) + "     Difficulty: " + difficulty)
	print("==========\\ ROOM /==========")
	cards_ascii.print_cards_side_by_side([deck_in_ascii[name] for name in room.card_seq])
	print("\n==========\\ YOU /==========\n")
	print(f"HP: {player.hp}")
	print(f"Current strenght: {player.current_weapon}")
	print(f"Last card killed: {player.last_card_killed}")
	print(f"Cards left: {len(room.deck)}")
	print("\n==========\\ ACTIONS /==========\n")
	
	# Actions:
	print("1 - Select card")
	cards_suits = [deck[c].suit for c in room.card_seq]
	
	print("2 - Skip" if room.skipped_last == False and not room.played_first_card or infinite_skips == True else strike("2 - Skip"))
	
	raw_action = get_input("# ", str)
	while raw_action not in ["1", "2", "34", "63", "86", "420", "~"]:
		raw_action = get_input("Invalid input!\n\n# ", str, "")
	
	if raw_action == "~":
		code = input("Enter the desired code:\n# ")
		if code.isnumeric():
			code = int(code)
			if code == 34:
				can_die = not can_die
				print(f"can_die state: {can_die}")
				input()
			if code == 63:
				print(f"Seed: {seed}")
				input()
			if code == 86 and first_game_action == False:
				elapsed_time = int(time.time() - start_time)
				minutes = elapsed_time // 60
				seconds = elapsed_time % 60
				print(f"Run time: {minutes:02d}:{seconds:02d}")
				input()
			if code == 420:
				infinite_skips = not infinite_skips
				print(f"infinite_skips state: {infinite_skips}")
				input()
		else:
			if code == "print_deck":
				cards_ascii.print_cards_side_by_side([deck_in_ascii[name] for name in room.deck])
				input()
			if code == "save":
				save_state(save_state_vars, SAVE_STATE_FILE)
			if code == "load":
				load_state(SAVE_STATE_FILE)
			if code.startswith("/set"):
			    try:
			        # Parse
			        parts = code.split(None, 2)
			        if len(parts) != 3:
			            print("Usage: /set [variable] [value]")
			            input()
			            continue
			        
			        var_path = parts[1]
			        value_str = parts[2]
			        
			        try:
			            new_value = eval(value_str)
			        except:
			            # If eval fails, try parsing as number or string
			            if value_str.replace("_", "").isdigit():
			                new_value = int(value_str.replace("_", ""))
			            else:
			                new_value = value_str
			        
			        if "." not in var_path and "[" not in var_path:
			            globals()[var_path] = new_value
			            print(f"Set {var_path} = {new_value}")
			        
			        elif "." in var_path and "[" not in var_path:
			            obj_name, attr_name = var_path.split(".", 1)
			            obj = globals()[obj_name]
			            setattr(obj, attr_name, new_value)
			            print(f"Set {var_path} = {new_value}")
			        
			        else:
			            # Use exec to handle assignments
			            exec(f"{var_path} = {repr(new_value)}")
			            print(f"Set {var_path} = {new_value}")
			        
			        input()
			    
			    except Exception as e:
			        print(f"Error setting variable: {e}")
			        input()
			    
			    continue
			elif code.startswith("/exec"):
				try:
					parts = code.split(None, 1)
					if len(parts) < 2:
						print("Usage: /exec <python_code>")
						input()
						continue
					
					exec_code = parts[1].strip()
					
					try:
						result = eval(exec_code, globals())
						if result is not None:
							print(f"Result: {result}")
						else:
							print("Executed successfully")
					except SyntaxError:
						exec(exec_code, globals())
						print("Executed successfully")
					
					input()
				
				except AttributeError as e:
					print(f"Attribute Error: {e}")
					print("Object or method doesn't exist")
					input()
				
				except IndexError as e:
					print(f"Index Error: {e}")
					print("Index out of bounds")
					input()
				
				except NameError as e:
					print(f"Name Error: {e}")
					print("Variable or object not defined")
					input()
				
				except TypeError as e:
					print(f"Type Error: {e}")
					print("Incompatible types or wrong arguments")
					input()
				
				except Exception as e:
					print(f"Error: {type(e).__name__}")
					print(f"Details: {e}")
					input()
				
				continue
	if not raw_action.isnumeric():
		print("Invalid input!")
		continue
	
	action = int(raw_action)
	
	# Select card
	if action == 1:
		room.played_first_card = True
		if len(room.card_seq) < 9:
			select_card = get_input(f"\nSelect the card (1 - {len(room.card_seq)}, or 0 to cancel):\n# ", str)
		else:
			select_card = input(f"\nSelect the card (1 - {len(room.card_seq)}, or 0 to cancel):\n# ")
		
		if select_card == "0":
			continue
		
		num_opt = [i+1 for i in range(len(room.card_seq))]
		
		while not select_card.isnumeric():
			select_card = get_input("\n# ", str)
				
		select_card = int(select_card)
		
		if str(select_card) == "0":
			continue
		
		while select_card not in num_opt:
			select_card = get_input("\n# ", str)
			while not select_card.isnumeric():
				select_card = get_input("\n# ", str)
			select_card = int(an)
		
		if first_game_action:
			start_time = time.time()
			first_game_action = False
	
		# Store selected card
		selected_card_name = room.card_seq[select_card - 1]
		selected_card = deck[selected_card_name]
	
		# Heal
		if selected_card.get_suit() == "hearts":
			heal_amount = selected_card.strength()
			
			if heal_amount > highest_heal:
				highest_heal = heal_amount
				
			if not room.heal_used:
				player.heal(heal_amount)
				room.heal_used = True
				print(f"You healed for {heal_amount} HP!")
				input("Press enter to continue...")
			else:
				print(f"You discarded {heal_amount} heal!")
				input("Press enter to continue...")
	
		# Deal damage
		elif selected_card.get_suit() in ["spades", "clubs"]:
			sel_card_strenght = selected_card.strength()
			
			last_killed_card = player.last_card_killed
			weapon = player.current_weapon
			
			if sel_card_strenght > highest_card_killed:
				highest_card_killed = sel_card_strenght
			
			# Default: full damage
			damage = sel_card_strenght
			
			if player.current_weapon > 0 and (last_killed_card >= sel_card_strenght or last_killed_card == 0) and weapon > 0:
				print("Do you want to use your weapon?\n1 - Yes\n2 - No")
				an = get_input("# ", str)
				while not an.isnumeric():
					an = get_input("\n# ", str)
				
				an = int(an)
				
				while an not in [1, 2]:
					an = get_input("\n# ", str)
					while not an.isnumeric():
						an = get_input("\n# ", str)
					an = int(an)
			
				if an == 1:
					use_weapon = True
				else:
					use_weapon = False
			
			if (last_killed_card >= sel_card_strenght or last_killed_card == 0) and weapon > 0 and use_weapon:
				damage = max(0, sel_card_strenght - weapon)
				player.last_card_killed = sel_card_strenght
				
				if highest_damage < damage:
					highest_damage = damage
			else:
				damage = sel_card_strenght
				if highest_damage < damage:
					highest_damage = damage
			
			player.take_damage(damage)
			print(f"You got hit by {damage} damage!")
			input("Press enter to continue...")
		
		# Get weapon/discard a weapon
		elif selected_card.get_suit() == "diamonds":
			new_strenght = selected_card.strength()
			
			if player.current_weapon > 0:
				print("Do you want to discard or to equip the weapon?\n1 - Equip\n2 - Discard\n")
				an = get_input("# ", str)
				while not an.isnumeric():
					an = get_input("\n# ", str)
				
				an = int(an)
				
				while an not in [1, 2]:
					an = get_input("\n# ", str)
					while not an.isnumeric():
						an = get_input("\n# ", str)
					an = int(an)
				
				if an == 2:
					print(f"You discarded {new_strenght} strenght!")
					input("Press enter to continue...")
				else:
					player.current_weapon = new_strenght
					player.last_card_killed = 0
					print(f"You got {new_strenght} strenght!")
					input("Press enter to continue...")
			else:
				player.current_weapon = new_strenght
				print(f"You got {new_strenght} strenght!")
				input("Press enter to continue...")
			
			if highest_weapon < new_strenght:
				highest_weapon = new_strenght
		# Remove card
		room.choose_card(select_card)

	# Skip
	if action == 2 and (infinite_skips or (not room.skipped_last and not room.played_first_card)):
		if first_game_action:
			start_time = time.time()
			if infinite_skips == False:
				first_game_action = False
			else:
				first_game_action = True
			
		room.reset(4)
		rng_state_at_room_start = random.getstate()
		if infinite_skips == False:
			room.skipped_last = True
		else:
			room.skipped_last = False
	
	# Replenish cards when only 1 left
	if len(room.card_seq) < 2:
		if len(room.deck) > 0:
			# Normal card addition
			numbers_of_card_to_add = min(3, len(room.deck))
			room.add_cards(numbers_of_card_to_add)
			rng_state_at_room_start = random.getstate()
		elif endless_mode:
			# Deck is empty in endless mode - replenish!
			room.replenish_deck()
			rng_state_at_room_start = random.getstate()
		
		if endless_mode:
		    if difficulty == "easy":
		        saves["easy_high_score"] = current_room
		    else:
		        saves["normal_high_score"] = current_room
		    save_data()
		
		current_room += 1
		room.skipped_last = False
		room.heal_used = False
		room.played_first_card = False

	# Win condition - deck empty AND card_seq empty
	if len(room.deck) == 0 and len(room.card_seq) < 1 and not endless_mode:
		clean()
		print(""" __   _____  _   _  __        _____  _   _ _ 
 \ \ / / _ \| | | | \ \      / / _ \| \ | | |
  \ V / | | | | | |  \ \ /\ / / | | |  \| | |
   | || |_| | |_| |   \ V  V /| |_| | |\  |_|
   |_| \___/ \___/     \_/\_/  \___/|_| \_(_)
                   
                          """)
        
		elapsed_time = int(time.time() - start_time)
		minutes = elapsed_time // 60
		seconds = elapsed_time % 60
        
		print(f"Your seed: {seed}\nHighest damage you took: {highest_damage}\nHighest heal: {highest_heal}\nHighest card killed: {highest_card_killed}\nHighest weapon: {highest_weapon}\n\nRun time: {minutes:02d}:{seconds:02d}")
		
		game_over = True
		print("\n\nEndless mode?\n1 - Yes\n2 - No\n")
		an = get_input("# ", str)
		while not an.isnumeric():
			an = get_input("\n# ", str)
				
		an = int(an)
				
		while an not in [1, 2]:
			an = get_input("\n# ", str)
			while not an.isnumeric():
				an = get_input("\n# ", str)
			an = int(an)
		if an == 1:
			room.replenish_deck()
			endless_mode = True
			game_over = False
		else:
			endless_mode = False
	
	# lose condition
	if player.hp <= 0 and can_die == True:
		clean()
		print("""__  __               __           __     
\ \/ /___  __  __   / /___  _____/ /_    
 \  / __ \/ / / /  / / __ \/ ___/ __/    
 / / /_/ / /_/ /  / / /_/ (__  ) /_      
/_/\____/\__,_/  /_/\____/____/\__/      
                                         """)

		elapsed_time = int(time.time() - start_time)
		minutes = elapsed_time // 60
		seconds = elapsed_time % 60

		if endless_mode == True:
			print(f"You survived: {current_room} rooms!")
			
		print(f"Your seed: {seed}\nHighest damage you took: {highest_damage}\nHighest heal: {highest_heal}\nHighest card killed: {highest_card_killed}\nHighest weapon: {highest_weapon}\nIn room: {current_room}\n\nRun time: {minutes:02d}:{seconds:02d}\nDifficulty: {difficulty}")
		input()
		
		game_over = True
		endless_mode = False