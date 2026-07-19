from django.db import models

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.http import Http404
class Room(models.Model):
    game_type = models.CharField(max_length=50 , blank=True )
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Player(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    order = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    truths_remaining = models.IntegerField(default=5)
    dares_remaining = models.IntegerField(default=5)
    truth_streak = models.IntegerField(default=0)  # Tracks "in a row"

    def __str__(self):
        return self.name

    def get_next_player(players, current_index):
        if current_index + 1 >= len(players):
            return 0
        return current_index + 1

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    nickname = models.CharField(max_length=50)
    score = models.IntegerField(default=0)

    def __str__(self):
        return self.nickname


import uuid
import random
import string


class Rooms(models.Model):
    game_type = models.CharField(max_length=50,blank=True)
    room_code = models.CharField(max_length=6, unique=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    turn_index = models.PositiveIntegerField(default=0)
    last_host_heartbeat = models.DateTimeField(null=True, blank=True)
    current_scores = models.JSONField(default=dict)
    total_scores = models.JSONField(default=dict)  # Lifetime points
    last_winner = models.CharField(max_length=255, null=True, blank=True)
    voted_users = models.JSONField(default=list)
    last_action_text = models.TextField(null=True, blank=True)
    # State Control
    STATUS_CHOICES = [
        ('LOBBY', 'Lobby'),
        ('PLAYING', 'In Progress'),
        ('FINISHED', 'Finished'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='LOBBY')

    # Membership
    players = models.ManyToManyField(Profile)
    max_capacity = models.IntegerField(default=5)  # Perfect for Math 1-1

    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    current_turn_index = models.IntegerField(default=0)
    last_action_text = models.TextField(blank=True)
    latest_proof_url = models.CharField(max_length=500, null=True, blank=True)
    voting_active = models.BooleanField(default=False)
    voting_yes_users = models.JSONField(default=list, blank=True)  # Usernames who voted Yes
    voting_no_users = models.JSONField(default=list, blank=True)  # Usernames who voted No
    voted_item_type = models.CharField(max_length=10, null=True, blank=True)  # "truth" or "dare"

    def get_current_player(self):
        all_players = self.players.all().order_by('id')
        if not all_players.exists(): return None
        return all_players[self.current_turn_index % all_players.count()]

    def next_turn(self):
        self.current_turn_index += 1
        self.last_action_text = ""  # Clear the screen for the next person
        self.save()

    def is_full(self):
        return self.players.count() >= self.max_capacity

    def check_host_status(self):
        """
        Checks if the host has been silent for more than 30 seconds.
        If they are gone, it triggers the reassignment logic.
        """
        # If the game is finished, we don't care about the host anymore
        if self.status == 'FINISHED':
            return

        timeout_limit = timezone.now() - timedelta(seconds=30)

        if self.last_host_heartbeat < timeout_limit:
            self.reassign_host()

    def reassign_host(self):
        """
        Finds the next available player to take over as host.
        """
        # Get all players currently in the room except the old host
        other_players = self.players.exclude(user=self.host)

        if other_players.exists():
            # Promote the person who joined the room first (or just the first in the list)
            new_host_profile = other_players.first()
            self.host = new_host_profile.user
            self.last_host_heartbeat = timezone.now()  # Reset the clock for the new host
            self.save()
        else:
            # If no one else is in the room, just end the game
            self.status = 'FINISHED'
            self.save()

from django.db import models


class Game(models.Model):
    title = models.CharField(max_length=100)  # e.g., "Math 1-1"
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='game_images/', blank=True, null=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()  # e.g., "What is 15 + 27?"
    correct_answer = models.CharField(max_length=255)
    points = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.game.title} - {self.text[:20]}"

class ChatMessage(models.Model):
    room = models.ForeignKey(Rooms, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    is_sticker = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    file_url = models.CharField(max_length=500, null=True, blank=True)

class DevilsPokerSession(models.Model):
    STAGE_CHOICES = [
        ('SETUP', 'Setup Phase'),
        ('GUESSING', 'Guessing Phase'),
        ('PENALTY', 'Truth Penalty Phase'),
        ('FINISHED', 'Game Over'),
    ]

    room = models.OneToOneField('Rooms', on_delete=models.CASCADE, related_name='poker_session')
    player1 = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True, related_name='poker_p1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,related_name='poker_p2')

    # Store hands as comma-separated strings of indices, e.g., "R,R,B,R,R"
    # Index position corresponds to Card 1, 2, 3, 4, 5
    p1_hand = models.CharField(max_length=50, default="")
    p2_hand = models.CharField(max_length=50, default="")

    # Track which cards are still active in the game (e.g., "0,1,2,3,4")
    # When a player guesses wrong, we remove one of their opponent's Red ('R') card indices from this active list
    p1_active_indices = models.CharField(max_length=50, default="0,1,2,3,4")
    p2_active_indices = models.CharField(max_length=50, default="0,1,2,3,4")

    current_turn = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True, related_name='poker_turns')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='SETUP')

    # Fallback storage for when a player guesses wrong and must answer a question
    active_penalty_question = models.TextField(blank=True, null=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='poker_wins')

    def deal_cards(self):
        """Randomly generates hands with 4 Reds ('R') and 1 Black ('B') card for both players."""
        p1_cards = ['R', 'R', 'R', 'R', 'B']
        p2_cards = ['R', 'R', 'R', 'R', 'B']

        random.shuffle(p1_cards)
        random.shuffle(p2_cards)

        self.p1_hand = ",".join(p1_cards)
        self.p2_hand = ",".join(p2_cards)
        self.p1_active_indices = "0,1,2,3,4"
        self.p2_active_indices = "0,1,2,3,4"
        self.stage = 'GUESSING'
        self.save()

    def get_hand_list(self, player_num):
        hand_str = self.p1_hand if player_num == 1 else self.p2_hand
        return hand_str.split(",")

    def get_active_indices(self, player_num):
        indices_str = self.p1_active_indices if player_num == 1 else self.p2_active_indices
        return [int(x) for x in indices_str.split(",") if x.strip() != ""]

    def make_guess(self, guessing_user, target_index):
        """
        Processes a guess from the guessing_user on their opponent's hand at target_index.
        """
        if self.stage != 'GUESSING' or self.current_turn != guessing_user:
            return {"status": "error", "message": "It is not your turn or stage to guess."}

        # Determine who is defending
        is_p1_guessing = (guessing_user == self.player1)
        defender = self.player2 if is_p1_guessing else self.player1
        defending_player_num = 2 if is_p1_guessing else 1

        defender_hand = self.get_hand_list(defending_player_num)
        defender_active = self.get_active_indices(defending_player_num)

        if target_index not in defender_active:
            return {"status": "error", "message": "That card has already been eliminated!"}

        # --- CASE 1: CORRECT GUESS (GUESSER WINS) ---
        if defender_hand[target_index] == 'B':
            self.winner = guessing_user
            self.stage = 'FINISHED'
            self.save()
            return {"status": "win",
                    "message": f"{guessing_user.username} guessed correctly! The Devil Card was at position {target_index + 1}."}

        # --- CASE 2: INCORRECT GUESS (PENALTY INITIATED) ---
        else:
            # 1. Defender loses a Red card from their active hand (not the Black card 'B')
            red_indices = [i for i in defender_active if defender_hand[i] == 'R' and i != target_index]

            # If they have red cards left to eliminate, remove one randomly or remove the guessed card
            if target_index in red_indices:
                defender_active.remove(target_index)
            elif red_indices:
                # Fallback safeguard: remove a random active red card if the guessed card wasn't red
                defender_active.remove(random.choice(red_indices))

            # Update the defender's active cards list
            new_active_str = ",".join(str(x) for x in defender_active)
            if is_p1_guessing:
                self.p2_active_indices = new_active_str
            else:
                self.p1_active_indices = new_active_str

            # 2. Trigger the penalty phase: Guesser must answer a question
            self.stage = 'PENALTY'
            # (You can pull a random Truth question from your database here)
            self.active_penalty_question = "Tell us a secret you've never told anyone in this room."
            self.save()

            return {
                "status": "penalty",
                "message": f"Incorrect! {guessing_user.username} must answer a Truth question. {defender.username} loses a Red card!"
            }

    def resolve_penalty(self):
        """Swaps turn to the opponent once the truth question is answered."""
        if self.stage != 'PENALTY':
            return

        # Swap current turn to the other player
        self.current_turn = self.player2 if self.current_turn == self.player1 else self.player1
        self.stage = 'GUESSING'
        self.active_penalty_question = None
        self.save()