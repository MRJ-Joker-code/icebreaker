from django.shortcuts import render, redirect
from .models import Room
import random
import string
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils import timezone
from datetime import timedelta
# The "Cartridges" - Add new games here without changing any other code
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Centralized Hub: Contains dynamic question banks AND rich front-facing metadata description notes
GAMES_LIBRARY = {
    'math-1-1': {
        'title': 'Math 1v1 Arena',
        'emoji': '📐',
        'banner_class': 'banner-math',
        'description': (
            "Go head-to-head in a high-stakes, fast-paced mental arithmetic challenge! "
            "Players take turns resolving equations against a ticking clock. Ideal for finding out "
            "who has the sharpest computational speed under heavy cognitive pressure."
        ),
        'questions': [
            "Solve: 15 + 27",
            "What is the square root of 64?",
            "If x + 5 = 12, what is x?",
            "How many degrees are in a right angle?"
        ]
    },
    'truth-or-dare': {
        'title': 'Truth or Dare',
        'emoji': '🤐',
        'banner_class': 'banner-truth',
        'description': (
            "The quintessential social icebreaker party experience. Face deep secrets or complete "
            "absurd, hilarious performance dares on stream. Perfect for friend groups looking to "
            "break down corporate walls or spice up a late-night call."
        ),
        'questions': [
            "TRUTH: What is your most used emoji?",
            "DARE: Mute your mic and try to act out 'Pizza' until someone guesses it.",
            "TRUTH: What was the last thing you ate?"
        ]
    },
    'icebreaker': {
        'title': 'Icebreaker Express',
        'emoji': '👋',
        'banner_class': 'banner-default',
        'description': (
            "Skip the standard, dry conversational starters and small talk. This pool serves up "
            "thought-provoking, imaginative entry questions designed to establish comfortable chemistry "
            "and uncover unique fun facts about everyone in your group."
        ),
        'questions': [
            "If you could travel anywhere right now, where would you go?",
            "What is your favorite hobby?",
            "What's one thing you're looking forward to this week?"
        ]
    },
    'most-likely': {
        'title': 'Most Likely To...',
        'emoji': '👥',
        'banner_class': 'banner-most',
        'description': (
            "Expose your squad's chaotic traits! Players vote anonymously on outrageous, specific scenarios "
            "to crown who in their circle fits the profile best. Warning: This mode has a record of "
            "sparking highly entertaining debates over player behavioral tendencies."
        ),
        'questions': [
            "Most likely to accidentally join a cult?",
            "Most likely to survive a zombie apocalypse?",
            "Most likely to become a billionaire?",
            "Most likely to forget their own birthday?",
            "Most likely to walk into a glass door?",
            "Most likely to get arrested for something harmless?",
            "Most likely to own 10 cats?",
            "Most likely to win an Olympic medal for sleeping?",
            "Most likely to be a secret agent?",
            "Most likely to move to another country on a whim?"
        ]
    }
}


@login_required
def game_detail_view(request, game_key):
    """Intermediate routing page pulling descriptions straight from our structured dictionary."""
    game_config = GAMES_LIBRARY.get(game_key)

    if not game_config:
        return redirect('dashboard')

    context = {
        'game_key': game_key,
        'title': game_config['title'],
        'emoji': game_config['emoji'],
        'banner_class': game_config['banner_class'],
        'description': game_config['description'],
        'prompt_count': len(game_config['questions']),
        'nickname': request.user.username
    }
    return render(request, 'gamesd.html', context)
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

from django.utils import timezone


def home(request):
    if request.method == "POST":
        room_name = request.POST.get("create_room")

        if room_name:
            code = generate_code()

            room = Room.objects.create(
                name=room_name,
            )

            return redirect("room", room_name=room.name)

    return render(request, "gamehome.html")


def join_room(request):
    code = request.GET.get("room")

    try:
        room = Room.objects.get(name=code)
        return redirect("room", room_name=room.name)
    except:
        return redirect("home")


from django.contrib.auth import login
from .models import Profile

def signup(request):
    if request.method == "POST":
        full_name = request.POST.get('name')
        user_email = request.POST.get('email')
        nickname = request.POST.get('nickname')
        user_password = request.POST.get('password')

        if not all([full_name, user_email, nickname, user_password]):
            return render(request, 'signup.html', {'error': 'All fields are required!'})

        try:
            new_user = User.objects.create_user(
                username=nickname,
                email=user_email,
                password=user_password,
                first_name=full_name
            )

            Profile.objects.create(
                user=new_user,
                name=full_name,
                email=user_email,
                nickname=nickname
            )

            return redirect('dashboard')

        except Exception as e:
            return render(request, 'signup.html', {'error': str(e)})

    return render(request, 'signup.html')


@login_required
def dashboard(request):
    game_list = GAMES_LIBRARY.keys()
    return render(request, 'dashboard.html', {
        'games': GAMES_LIBRARY, # We send the whole library instead of just .keys()
        'nickname': request.user.profile.nickname # Keeps your exact profile nickname setup
    })


from django.contrib.auth import authenticate, login
from django.contrib import messages


def login_view(request):
    if request.method == "POST":
        u_name = request.POST.get('nickname')
        u_pass = request.POST.get('password')

        user = authenticate(request, username=u_name, password=u_pass)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid nickname or password")

    return render(request, "login.html")

from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect('login')


import random
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Rooms, Game # Updated to 'Rooms'

@login_required
def create_room(request, game_key):
    # Check if the key exists in our library
    if game_key not in GAMES_LIBRARY:
        return redirect('dashboard')

    # Generate a random 4-digit code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    # Create the Room record
    new_room = Rooms.objects.create(
        room_code=code,
        host=request.user,
        game_type=game_key,  # Saves 'math-1-1' or 'icebreaker'
        status='LOBBY'
    )

    new_room.players.add(request.user.profile)
    return redirect('room_lobby', room_code=code)

@login_required
def join_room(request):
    if request.method == "POST":
        code = request.POST.get('room_code').upper()
        try:
            # Look up in 'Rooms' table
            room = Rooms.objects.get(room_code=code, status='LOBBY')

            if room.players.count() >= room.max_capacity:
                return render(request, 'dashboard.html', {'error': 'Room is full!'})

            room.players.add(request.user.profile)
            return redirect('room_lobby', room_code=code)

        except Rooms.DoesNotExist:
            return render(request, 'dashboard.html', {'error': 'Invalid Room Code'})

    return redirect('dashboard')

@login_required
def start_game(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    if room.host == request.user:
        room.status = 'PLAYING'
        room.save()

        # Always redirect to room_session.
        # room_session will decide which template to show based on game_type.
        return redirect('room_session', room_code=room.room_code)

    return redirect('room_session', room_code=room.room_code)


@login_required
def room_session(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    try:
        # Pull the player profile record bound to the user requesting this page
        me = room.players.get(user=request.user)
    except Exception:
        return redirect('dashboard')

    # 1. FETCH ALL PLAYERS IN THE ROOM
    players = room.players.all()
    player_count = players.count()

    # 2. HANDLE INTERACTIVE ACTION SUBMISSIONS (POST REQUESTS)
    if request.method == "POST":
        action = request.POST.get('action')

        # Calculate the current player profile in the hot seat using turn_index loop math
        current_hot_seat_player = players[room.turn_index % player_count] if player_count > 0 else None

        # A. HOST CONTROLLER PROCESSING ACTION
        if request.user == room.host:
            if action == 'next_player':
                if player_count > 0:
                    room.turn_index += 1
                    room.current_truth_dare = "Waiting for choice..."
                    room.save()
                    return JsonResponse({'status': 'success'})

        # B. ACTIVE HOT SEAT CONTROLLER PROCESSING ACTION
        # Verify if the current user profile matches the active profile calculated by turn index
        if current_hot_seat_player and request.user == current_hot_seat_player.user:
            if action == 'pick_truth':
                if me.truths_remaining > 0 and me.truth_streak < 3:
                    me.truths_remaining -= 1
                    me.truth_streak += 1
                    room.current_truth_dare = random.choice(TRUTH_LIST)
                    me.save()
                    room.save()
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': 'Cannot pick Truth!'}, status=400)

            elif action == 'pick_dare':
                if me.dares_remaining > 0:
                    me.dares_remaining -= 1
                    me.truth_streak = 0  # Break and reset the truth streak!
                    room.current_truth_dare = random.choice(DARE_LIST)
                    me.save()
                    room.save()
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': 'No Dares left!'}, status=400)

        return JsonResponse({'status': 'error', 'message': 'Invalid action parameters'}, status=400)

    # 3. CALCULATE HOT SEAT PLAYER PROFILE FOR RENDER CONTEXT (GET REQUESTS)
    current_p = players[room.turn_index % player_count] if player_count > 0 else None

    context = {
        'room': room,
        'me': me,
        'is_host': room.host == request.user,
        # Safely determine hot seat state by comparing user objects!
        'is_hot_seat': (current_p.user == request.user) if current_p else False,
    }

    # 4. EXPLICIT GAME LIBRARY TEMPLATE DISPATCHER
    if room.game_type == 'truth-or-dare' or room.game_type == 'icebreaker':
        print(f"[ROUTER] Route Match: Serving Truth & Dare Frame Layout via '{room.game_type}' key.")
        return render(request, 'truth.html', context)

    elif room.game_type == 'most-likely' or room.game_type == 'math-1-1':
        print(f"[ROUTER] Route Match: Serving Most Likely Frame Layout via '{room.game_type}' key.")
        return render(request, 'game.html', context)

    else:
        print(f"[ROUTER] Unknown configuration key layout match fallback rule triggered for: {room.game_type}")
        return render(request, 'lobby.html', context)

@login_required
def end_game(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    if room.host == request.user:
        room.status = 'FINISHED'
        room.save()
    return redirect('game_results', room_code=room.room_code)


@login_required
def game_results(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    # Instead of calling a model method, we do the query here
    all_players = room.players.all().order_by('-score')

    # Get top 3 for the podium
    top_3 = all_players[:3]

    context = {
        'room': room,
        'all_players': all_players,
        'top_3': top_3,
        'is_host': room.host == request.user
    }
    return render(request, 'gameresults.html', context)

from django.http import JsonResponse


@login_required
def icebreaker(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    if room.status != 'PLAYING':
        return redirect('room_lobby', room_code=room.room_code)

    players = list(room.players.all())
    current_player_profile = players[room.turn_index % len(players)] if players else None

    if request.method == "POST":
        action = request.POST.get('action')
        prompts = GAMES_LIBRARY.get('icebreaker', ["Ready to play?"])

        # Leave Logic (Available to everyone)
        if action == "leave_game":
            room.players.remove(request.user.profile)
            if request.user == room.host:
                room.status = 'FINISHED'
            room.save()
            return JsonResponse({'status': 'redirect', 'url': '/dashboard/'})

        # Host-Only Controls
        if request.user == room.host:
            if action == "next_turn":
                room.turn_index += 1
                room.last_action_text = random.choice(prompts)
            elif action == "shuffle":
                room.last_action_text = random.choice(prompts)
            elif action == "end_game":
                room.status = 'FINISHED'

            room.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})

    return render(request, 'icebreaker.html', {
        'room': room,
        'current_player': current_player_profile,
        'is_host': (request.user == room.host),
        'prompt': room.last_action_text or "Press Shuffle to Start!"
    })
# DELETE THE OLD 'def room(request, room_name):' VIEW COMPLETELY.
# It is the one forcing "roomgame.html" on you.
@login_required
def room_lobby(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    # If the game has started, redirect to the specific view for THAT game
    if room.status == 'PLAYING':
        # This will redirect to 'icebreaker', 'math_game', or 'truth_or_dare'
        # based on whatever you saved in room.game_type
        return redirect('play_game', game_type=room.game_type, room_code=room.room_code)

    # Otherwise, stay in the lobby
    return render(request, 'lobby.html', {
        'room': room,
        'players': room.players.all(),
        'is_host': (room.host == request.user)
    })


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Rooms, ChatMessage

def send_message(request, room_code):
    if request.method == 'POST':
        room = get_object_or_404(Rooms, room_code=room_code)
        content = request.POST.get('content')
        is_sticker = request.POST.get('is_sticker') == 'true'

        msg = ChatMessage.objects.create(
            room=room,
            user=request.user,
            content=content,
            is_sticker=is_sticker
        )
        return JsonResponse({'status': 'sent'})


from django.http import JsonResponse


def get_messages(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    messages = room.messages.all().order_by('-timestamp')[:20]

    data = [
        {
            'user': m.user.username,
            'content': m.content,
            'is_sticker': m.is_sticker
        } for m in messages
    ]
    return JsonResponse({'messages': data[::-1]})


from django.http import JsonResponse




import random
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


@login_required
def most_likely(request, room_code, game_type):
    room = get_object_or_404(Rooms, room_code=room_code)
    game_data = GAMES_LIBRARY.get(game_type, ["No prompts found"])
    prompts = game_data if isinstance(game_data, list) else game_data.get('prompts', ["No prompts found"])

    if request.method == "POST":
        action = request.POST.get('action')

        # --- MANDATORY: END GAME ACTION ---
        if action == "end_game" and request.user == room.host:
            room.status = "FINISHED"  # Ensure your model has a status field
            room.save()
            return JsonResponse({'status': 'success'})

        # --- CAST VOTE ---
        if action == "cast_vote":
            voted_list = room.voted_users or []
            if request.user.username not in voted_list:
                target = request.POST.get('target')
                scores = room.current_scores or {}
                scores[target] = scores.get(target, 0) + 1
                voted_list.append(request.user.username)
                room.current_scores = scores
                room.voted_users = voted_list

                # Check for round completion
                if len(voted_list) >= room.players.count():
                    winner = max(scores, key=scores.get)
                    room.last_winner = winner
                    totals = room.total_scores or {}
                    totals[winner] = totals.get(winner, 0) + 1
                    room.total_scores = totals
                room.save()
                return JsonResponse({'status': 'success'})

        # --- NEXT TURN ---
        if action == "next_turn" and request.user == room.host:
            room.last_action_text = random.choice(prompts)
            room.current_scores = {p.user.username: 0 for p in room.players.all()}
            room.voted_users = []
            room.save()
            return JsonResponse({'status': 'success'})

    return render(request, 'game.html', {'room': room, 'is_host': (request.user == room.host)})


from django.shortcuts import get_object_or_404
from django.http import JsonResponse


def get_room_status(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    players = room.players.all()
    player_count = players.count()

    has_voted = request.user.username in (room.voted_users or [])
    voted_count = len(room.voted_users or [])

    # AUTOMATIC WINNER CALCULATION (Keep your original code)
    if player_count > 0 and voted_count >= player_count and room.status == "ACTIVE":
        if room.current_scores:
            calculated_winner = max(room.current_scores, key=room.current_scores.get)
            if not room.last_winner:
                room.last_winner = calculated_winner
                new_totals = room.total_scores or {}
                new_totals[calculated_winner] = new_totals.get(calculated_winner, 0) + 1
                room.total_scores = new_totals
                room.save()

    # Determine current game state info based on who is playing
    # First check your specific model assignment, fallback to index loop math
    target_username = "???"
    if hasattr(room, 'target_player') and room.target_player:
        target_username = room.target_player.username
    else:
        current_p = players[room.turn_index % player_count] if player_count > 0 else None
        if current_p:
            target_username = getattr(current_p, 'nickname', current_p.user.username)

    # Fetch player stats matching the user requesting the status check
    me_profile = room.players.filter(user=request.user).first()
    streak = getattr(me_profile, 'truth_streak', 0)
    truths_left = getattr(me_profile, 'truths_remaining', 5)
    dares_left = getattr(me_profile, 'dares_remaining', 5)

    # Resolve active card prompt text across both potential game fields safely
    active_prompt = "Waiting for choice..."
    if hasattr(room, 'current_truth_dare') and room.current_truth_dare:
        active_prompt = room.current_truth_dare
    elif room.last_action_text:
        active_prompt = room.last_action_text

    return JsonResponse({
        'status': room.status,
        'game_type': getattr(room, 'game_type', 'truth-or-dare'),
        'prompt': active_prompt,
        'target_player': target_username,
        'last_winner': room.last_winner,
        'round_id': f"{room.last_action_text or 'round'}_{room.last_winner or 'none'}",
        'has_voted': has_voted,
        'is_finished': "YES" if room.status == "FINISHED" else "NO",
        'is_my_turn': (room.target_player == request.user) if hasattr(room,
                                                                      'target_player') and room.target_player else False,

        # Player specific counters for meters
        'truth_streak': streak,
        'truths_remaining': truths_left,
        'dares_remaining': dares_left,
        'scores': room.current_scores or {},
        'total_scores': room.total_scores or {},
    })

@login_required
def truth_dare_game(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    # Get the player object for the current logged-in user
    me = room.players.get(user=request.user)

    if request.method == "POST":
        action = request.POST.get('action')

        # --- HOST ONLY ACTIONS ---
        if request.user == room.host:
            if action == 'next_player':
                players = room.players.all()
                if players.exists():
                    new_target = random.choice(players)
                    room.target_player = new_target.user
                    room.current_truth_dare = "Waiting for choice..."
                    room.save()
                    return JsonResponse({'status': 'success'})

        # --- PLAYER IN HOT SEAT ACTIONS ---
        if request.user == room.target_player:
            if action == 'pick_truth':
                if me.truths_remaining > 0 and me.truth_streak < 3:
                    me.truths_remaining -= 1
                    me.truth_streak += 1
                    room.current_truth_dare = random.choice(TRUTH_LIST)
                    me.save()
                    room.save()
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': 'Cannot pick Truth!'}, status=400)

            elif action == 'pick_dare':
                if me.dares_remaining > 0:
                    me.dares_remaining -= 1
                    me.truth_streak = 0  # Reset the streak!
                    room.current_truth_dare = random.choice(DARE_LIST)
                    me.save()
                    room.save()
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': 'No Dares left!'}, status=400)

    return render(request, 'truth.html', {
        'room': room,
        'me': me,
        'is_host': room.host == request.user,
        'is_hot_seat': room.target_player == request.user,
    })

@login_required
def pick_choice(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    player = get_object_or_404(Player, user=request.user, room=room)

    # Security: Only the person in the Hot Seat can pick
    if room.target_player != request.user:
        return JsonResponse({'error': 'Not your turn!'}, status=403)

    choice = request.POST.get('choice')  # 'truth' or 'dare'

    if choice == 'truth':
        # CHECK 1: Do they have truths left?
        if player.truths_remaining <= 0:
            return JsonResponse({'error': 'Out of Truths!'}, status=400)

        # CHECK 2: Are they on a 3-truth streak? (Double Dare enforcement)
        if player.truth_streak >= 3:
            return JsonResponse({'error': 'FORCE DARE! You must pick a Dare.'}, status=400)

        player.truths_remaining -= 1
        player.truth_streak += 1
        room.current_truth_dare = random.choice(TRUTH_LIST)

    elif choice == 'dare':
        player.dares_remaining -= 1
        player.truth_streak = 0  # Reset the streak!
        room.current_truth_dare = random.choice(DARE_LIST)

    player.save()
    room.save()
    return JsonResponse({'status': 'success'})