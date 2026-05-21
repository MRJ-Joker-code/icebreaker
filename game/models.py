from django.db import models

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

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