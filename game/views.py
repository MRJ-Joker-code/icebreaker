import random
import string
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Rooms, ChatMessage, Profile ,DevilsPokerSession # Assuming Profile is mapped here
from django.http import Http404
# ==========================================
# CENTRALIZED HUB: THE GAMES CARTRIDGES
# ==========================================
GAMES_LIBRARY = {
'devils-poker': {
    'title': "Devil's Poker",
    'emoji': '😈',
    'banner_class': 'banner-poker',
    'description': (
        "A high-stakes psychological 1v1 showdown! Bluff and read your opponent's "
        "hand of 5 cards to locate their hidden Black Devil card. A wrong guess strips away "
        "a card but forces a deep, raw Truth fallback penalty."
    ),
    'questions': [
        "What is a secret you have never shared with anyone in this room?",
        "What was the biggest lie you have ever told without getting caught?",
        "If you could trade lives with your opponent for a week, what is the first thing you would do?",
        "What is your absolute biggest insecurity when meeting someone new?"
    ]
},
    'truth-or-dare': {
        'title': 'Truth or Dare',
        'emoji': '🤐',
        'banner_class': 'banner-truth',
        'description': "The quintessential social icebreaker party experience.",
        'truths': [
            "What is your most used emoji?",
            "What was the last thing you ate?",
            "What is a secret you've never told anyone here?"
        ],
        'dares': [
            "Mute your mic and try to act out 'Pizza' until someone guesses it.",
            "Do 10 pushups on camera/stream.",
            "Show the last photo in your camera roll."
        ]
    },
    'icebreaker_play': {
        'title': 'Icebreaker Express',
        'emoji': '👋',
        'banner_class': 'banner-default',
        'description': "Skip the standard, dry conversational starters and small talk.",
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
        'description': "Expose your squad's chaotic traits! Players vote anonymously.",
        'questions': [
            "Most likely to accidentally join a cult?",
            "Most likely to survive a zombie apocalypse?",
            "Most likely to become a billionaire?",
            "Most likely to walk into a glass door?"
        ]
    }
}


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


# ==========================================
# AUTHENTICATION ENGINE ENTRIES
# ==========================================
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
            # Log user in directly upon registration
            login(request, new_user)
            return redirect('dashboard')
        except Exception as e:
            return render(request, 'signup.html', {'error': str(e)})

    return render(request, 'signup.html')


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


def logout_view(request):
    logout(request)
    return redirect('login')


# ==========================================
# CORE HUB PLATFORM DASHBOARDS
# ==========================================
@login_required
def dashboard(request):
    return render(request, 'dashboard.html', {
        'games': GAMES_LIBRARY,
        'nickname': request.user.profile.nickname
    })


@login_required
def game_detail_view(request, game_key):
    game_config = GAMES_LIBRARY.get(game_key)
    if not game_config:
        return redirect('dashboard')

    context = {
        'game_key': game_key,
        'title': game_config['title'],
        'emoji': game_config['emoji'],
        'banner_class': game_config['banner_class'],
        'description': game_config['description'],
        'prompt_count': len(game_config.get('questions', game_config.get('truths', []))),
        'nickname': request.user.username
    }
    return render(request, 'gamesd.html', context)


# ==========================================
# ROOM DISPATCH & MATCHMAKING OPERATIONS
# ==========================================
@login_required
def create_room(request, game_key):
    if game_key not in GAMES_LIBRARY:
        return redirect('dashboard')

    code = generate_code()
    new_room = Rooms.objects.create(
        room_code=code,
        host=request.user,
        game_type=game_key,
        status='LOBBY'
    )
    new_room.players.add(request.user.profile)
    return redirect('room_lobby', room_code=code)


@login_required
def join_room(request):
    """Players entering the room via code get funneled directly to where they belong."""
    if request.method == "POST":
        code = request.POST.get('room_code').upper()
        try:
            room = Rooms.objects.get(room_code=code)

            # If the game is already in progress, join and send them directly to the active screen
            if room.status == 'PLAYING':
                room.players.add(request.user.profile)
                return redirect(f"{room.game_type.replace('-', '_')}_play", room_code=room.room_code)

            # If it's still a lobby, send them to the shared waiting room
            elif room.status == 'LOBBY':
                if room.players.count() >= getattr(room, 'max_capacity', 10):
                    return render(request, 'dashboard.html', {'error': 'Room is full!'})
                room.players.add(request.user.profile)
                return redirect('room_lobby', room_code=code)

            else:
                return render(request, 'dashboard.html', {'error': 'This game has finished.'})

        except Rooms.DoesNotExist:
            return render(request, 'dashboard.html', {'error': 'Invalid Room Code'})

    return redirect('dashboard')


@login_required
def room_lobby(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    # If the game has started, route them instantly to their specific view
    if room.status == 'PLAYING':
        if room.game_type == 'icebreaker':
            return redirect('icebreaker_play', room_code=room.room_code)
        elif room.game_type == 'truth-or-dare':
            return redirect('truth_or_dare_play', room_code=room.room_code)
        elif room.game_type == 'most-likely':
            return redirect('most_likely_play', room_code=room.room_code)
        elif room.game_type == 'math-1-1':
            return redirect('math_1v1_play', room_code=room.room_code)
        # FIX: Check for 'devils-poker' instead of 'devils_poker_play'
        elif room.game_type == 'devils-poker':
            return redirect('devils_poker_play', room_code=room.room_code)

    return render(request, 'lobby.html', {
        'room': room,
        'players': room.players.all(),
        'is_host': (room.host == request.user)
    })

@login_required
def start_game(request, room_code):
    # Note: Using your explicit model name "Rooms"
    room = get_object_or_404(Rooms, room_code=room_code)

    if room.host == request.user:
        # 1. Clear out all persistent player win counts to 0 for a fresh game
        for player in room.players.all():
            if hasattr(player, 'score'):
                player.score = 0
                player.save()

        # 2. Reset live round scores dictionary if your model tracks it
        if hasattr(room, 'current_scores'):
            room.current_scores = {}

        # 3. Flip status to active
        room.status = 'PLAYING'
        room.save()

    # Maps directly to URLs like 'truth_dare_play' or 'most_likely_play'
    return redirect(f"{room.game_type.replace('-', '_')}_play", room_code=room.room_code)


def award_points(room, username, points):
    scores = room.current_scores or {}
    scores[username] = scores.get(username, 0) + points
    room.current_scores = scores
    room.save()


@login_required
def truth_dare_play(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    # Grab current player profile out of the room assignment pipeline
    me = room.players.filter(user=request.user).first()
    if not me:
        me = getattr(request.user, 'profile', None)

    current_player_profile = room.get_current_player()
    target_username = current_player_profile.user.username if current_player_profile else "???"

    # Determine whose numbers we are displaying/modifying
    active_profile = current_player_profile if current_player_profile else me

    # --- SAFE CHARGE PARSING & ENFORCEMENT ---
    if active_profile:
        try:
            active_profile.refresh_from_db()
        except Exception:
            pass

    # Safeguard fallback to defaults if database values are NULL/None
    raw_truths = getattr(active_profile, 'truths_remaining', 5)
    truths_val = int(raw_truths) if raw_truths is not None else 5

    raw_dares = getattr(active_profile, 'dares_remaining', 3)
    dares_val = int(raw_dares) if raw_dares is not None else 3

    raw_streak = getattr(active_profile, 'truth_streak', 0)
    streak_val = int(raw_streak) if raw_streak is not None else 0

    # Strict maximum enforcement per turn rules
    if truths_val > 5:
        truths_val = 5
    if dares_val > 3:
        dares_val = 3

    # --- 1. HANDLE POST REQUESTS (Button actions) ---
    if request.method == 'POST':
        action = request.POST.get('action')

        # FORCE AUTO-SWAP RULE: If out of charges, hijack the incoming action
        if truths_val <= 0 and action == 'pick_truth':
            action = 'pick_dare'
        elif dares_val <= 0 and action == 'pick_dare':
            action = 'pick_truth'

        if action == 'pick_truth' and truths_val > 0:
            truths_val -= 1
            streak_val += 1

            if active_profile:
                setattr(active_profile, 'truths_remaining', truths_val)
                setattr(active_profile, 'truth_streak', streak_val)
                try:
                    active_profile.save()
                except Exception as e:
                    print(f"Error saving profile: {e}")

            room.last_action_text = "Sample Truth: What is your biggest fear?"
            room.voted_item_type = 'truth'
            room.voting_active = True
            room.voting_yes_users = []
            room.voting_no_users = []
            room.save()

            return JsonResponse({
                'status': 'SUCCESS',
                'truths_remaining': truths_val,
                'dares_remaining': dares_val,
                'truth_streak': streak_val,
            })

        elif action == 'pick_dare' and dares_val > 0:
            dares_val -= 1
            streak_val = 0  # Reset streak to 0 on a Dare selection

            if active_profile:
                setattr(active_profile, 'dares_remaining', dares_val)
                setattr(active_profile, 'truth_streak', streak_val)
                try:
                    active_profile.save()
                except Exception as e:
                    print(f"Error saving profile: {e}")

            room.last_action_text = "Sample Dare: Sing a song loudly!"
            room.voted_item_type = 'dare'
            room.voting_active = True
            room.voting_yes_users = []
            room.voting_no_users = []
            room.save()

            return JsonResponse({
                'status': 'SUCCESS',
                'truths_remaining': truths_val,
                'dares_remaining': dares_val,
                'truth_streak': streak_val,
            })

        elif action == 'next_player':
            room.voting_active = False
            room.next_turn()
            return JsonResponse({'status': 'SUCCESS'})

        elif action == 'end_session':
            if room.host == request.user:
                room.status = 'FINISHED'
                room.save()
                return JsonResponse({'status': 'FINISHED'})
            return JsonResponse({'status': 'ERROR', 'message': 'Unauthorized'}, status=403)

    # --- 2. HANDLE ASYNC BACKGROUND POLLS (JSON data sync) ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'format' in request.GET or '_cb' in request.GET:
        if room.status == 'FINISHED':
            return JsonResponse({'status': 'FINISHED'})

        messages_query = ChatMessage.objects.filter(room=room).order_by('-timestamp')[:20]
        messages_list = [
            {
                'user': m.user.username,
                'content': m.content,
                'is_sticker': m.is_sticker
            } for m in messages_query
        ][::-1]

        has_voted = (request.user.username in (room.voting_yes_users or [])) or \
                    (request.user.username in (room.voting_no_users or []))

        return JsonResponse({
            'status': room.status,
            'target_player': target_username,
            'prompt': room.last_action_text or "Waiting for choice...",
            'latest_proof_url': getattr(room, 'latest_proof_url', None),

            'truth_streak': streak_val,
            'truths_remaining': truths_val,  # <-- Injected into live loop payload!
            'dares_remaining': dares_val,    # <-- Injected into live loop payload!

            'scores': room.current_scores or {},
            'messages': messages_list,
            'voting_active': room.voting_active,
            'voting_yes_count': len(room.voting_yes_users or []),
            'voting_no_count': len(room.voting_no_users or []),
            'has_voted': has_voted,
        })

    # --- 3. STANDARD PAGE INITIAL RENDERING ---
    context = {
        'room': room,
        'me': me,
        'is_host': room.host == request.user,
        'is_hot_seat': current_player_profile.user == request.user if current_player_profile else False,
        'truths_remaining': truths_val,  # <-- Injected into template loader!
        'dares_remaining': dares_val,    # <-- Injected into template loader!
    }
    return render(request, 'truth.html', context)

# --- 4. SUBMIT VOTE VIEW ---
@login_required
def submit_vote(request, room_code):
    if request.method == 'POST':
        room = get_object_or_404(Rooms, room_code=room_code)

        # Check if voting session is open
        if not room.voting_active:
            return JsonResponse({'status': 'FAILED', 'error': 'No active voting session'}, status=400)

        vote_choice = request.POST.get('vote')  # "yes" or "no"
        username = request.user.username

        # Prevent the person in the hot seat from voting on themselves
        current_player_profile = room.get_current_player()
        if current_player_profile and current_player_profile.user == request.user:
            return JsonResponse({'status': 'FAILED', 'error': 'You cannot vote on your own turn!'}, status=400)

        # Initialize JSON fields securely
        yes_list = room.voting_yes_users or []
        no_list = room.voting_no_users or []

        # Ensure user can only vote once (clears existing vote if they switch)
        if username in yes_list:
            yes_list.remove(username)
        if username in no_list:
            no_list.remove(username)

        # Register the new vote
        if vote_choice == 'yes':
            yes_list.append(username)
        elif vote_choice == 'no':
            no_list.append(username)

        room.voting_yes_users = yes_list
        room.voting_no_users = no_list
        room.save()

        # Dynamic Tally check: Has everyone else voted?
        # (Total players in room minus 1 for the player in the hot seat)
        total_eligible_voters = max(1, room.players.count() - 1)
        total_votes_cast = len(yes_list) + len(no_list)

        if total_votes_cast >= total_eligible_voters:
            # End the vote session
            room.voting_active = False
            active_username = current_player_profile.user.username

            # STRICTOR MATH: Must have strictly MORE Yes votes than No votes to pass (Ties result in 0 points)
            if len(yes_list) > len(no_list):
                points_to_award = 10 if room.voted_item_type == 'dare' else 5
                award_points(room, active_username, points_to_award)
                room.last_action_text = f"✅ {active_username} PASSED! (+{points_to_award} pts)"
            else:
                room.last_action_text = f"❌ {active_username} FAILED! (No points awarded)"

            room.save()

        return JsonResponse({'status': 'SUCCESS'})

    return JsonResponse({'status': 'FAILED'}, status=400)

def get_truth_dare_status(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    players = room.players.all()
    player_count = players.count()

    # --- 1. ABSOLUTE ZERO GUARD: If session ended, wipe the state immediately ---
    if room.status == 'FINISHED':
        return JsonResponse({
            'status': 'FINISHED',
            'prompt': 'Session Concluded',
            'target_player': 'None',
            'current_player': 'None',
            'last_winner': None,
            'has_voted': False,
            'truth_streak': 0,
            'truths_remaining': 5,
            'dares_remaining': 5
        })

    # --- 2. ACTIVE GAME PIPELINE ---
    current_p = players[room.turn_index % player_count] if player_count > 0 else None
    target_username = getattr(current_p, 'nickname', current_p.user.username) if current_p else "???"

    # Pull the profile of the player making the request to get their individual stats
    me_profile = room.players.filter(user=request.user).first()

    return JsonResponse({
        'status': room.status,
        'game_type': room.game_type,
        'prompt': getattr(room, 'current_truth_dare', room.last_action_text) or "Awaiting choices...",
        'target_player': target_username,
        'current_player': target_username,
        'last_winner': getattr(room, 'last_winner', None),
        'has_voted': request.user.username in (getattr(room, 'voted_users', []) or []),
        'truth_streak': getattr(me_profile, 'truth_streak', 0) if me_profile else 0,
        'truths_remaining': getattr(me_profile, 'truths_remaining', 5) if me_profile else 5,
        'dares_remaining': getattr(me_profile, 'dares_remaining', 5) if me_profile else 5,
        'latest_proof_url': room.latest_proof_url,
    })
def get_room_status(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    players = room.players.all()
    player_count = players.count()

    # --- SHARED DATA ---
    current_p = players[room.turn_index % player_count] if player_count > 0 else None
    target_username = getattr(current_p, 'nickname', current_p.user.username) if current_p else "???"

    data = {
        'status': room.status,
        'game_type': room.game_type,
        'prompt': getattr(room, 'current_truth_dare', room.last_action_text) or "Awaiting start...",
        'target_player': target_username,
        'current_player': target_username,
    }

    # --- BRANCH: MOST LIKELY TO INTERACTIVE CORE ---
    if room.game_type == 'most-likely':
        # 1. Initialize empty live score distribution bucket
        live_scores = {p.user.username: 0 for p in players}

        # 2. Tally live vote data safely from database model variables or memory maps
        # If tracking directly from your room fields, map incoming target data:
        current_votes_dict = getattr(room, 'current_scores', {}) or {}

        # Fallback dynamic counter logic: read from global/cached states or incoming post values
        # For now, let's safely pass down the active counts if saved to room fields
        if isinstance(current_votes_dict, dict):
            for user_key, count_val in current_votes_dict.items():
                if user_key in live_scores:
                    live_scores[user_key] = count_val

        # 3. Compile long-term leaderboard standings
        total_leaderboard = {p.user.username: getattr(p, 'score', 0) for p in players}

        session_key = f"vote_{room.room_code}_{room.turn_index}"
        has_voted_this_round = session_key in request.session

        data.update({
            'last_winner': getattr(room, 'current_truth_dare', None),
            'scores': live_scores,
            'total_scores': total_leaderboard,
            'has_voted': has_voted_this_round
        })

    elif room.game_type == 'truth-or-dare':
        me_profile = room.players.filter(user=request.user).first()
        data.update({
            'last_winner': getattr(room, 'last_winner', None),
            'has_voted': request.user.username in (getattr(room, 'voted_users', []) or []),
            'truth_streak': getattr(me_profile, 'truth_streak', 0) if me_profile else 0,
            'truths_remaining': getattr(me_profile, 'truths_remaining', 5) if me_profile else 5,
            'dares_remaining': getattr(me_profile, 'dares_remaining', 5) if me_profile else 5,
        })

    return JsonResponse(data)


@login_required
def send_message(request, room_code):  # Fixed the parameter name here!
    if request.method == 'POST':
        room = get_object_or_404(Rooms, room_code=room_code)

        # Grab content (checking both 'content' and 'message_text')
        content = request.POST.get('content') or request.POST.get('message_text')
        is_sticker = request.POST.get('is_sticker') == 'true'

        if content:
            ChatMessage.objects.create(
                room=room,
                user=request.user,
                content=content,
                is_sticker=is_sticker
            )
            return JsonResponse({'status': 'sent'})

    return JsonResponse({'status': 'failed'}, status=400)


def get_messages(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)
    messages_query = room.messages.all().order_by('-timestamp')[:20]
    data = [
        {
            'user': m.user.username,
            'content': m.content,
            'is_sticker': m.is_sticker
        } for m in messages_query
    ]
    return JsonResponse({'messages': data[::-1]})


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
    all_players = room.players.all().order_by('-score')
    return render(request, 'gameresults.html', {
        'room': room,
        'all_players': all_players,
        'top_3': all_players[:3],
        'is_host': room.host == request.user
    })

ICEBREAKER_PROMPTS = [
    "If you could travel anywhere right now, where would you go?",
    "What is your absolute favorite hobby or hidden talent?",
    "What is one thing you are looking forward to this week?",
    "If you could have dinner with any historical figure, who would it be?",
    "What's the best piece of advice you've ever received?",
    "What is your ultimate comfort food?",
    "Would you rather live in a cabin in the mountains or a house on the beach?",
    "What is the most adventurous thing you've ever done?",
    "What's a movie or book you can rewatch/reread over and over?",
    "If you could instantaneously learn any language, what would it be?"
]
@login_required
def icebreaker_play(request, room_code):
    room = get_object_or_404(Rooms, room_code=room_code)

    if room.status == 'FINISHED':
        return redirect('dashboard')

    players = room.players.all()
    player_count = players.count()

    # POST ACTION PROCESSING HUB
    if request.method == "POST":
        action = request.POST.get('action')

        if request.user == room.host:
            # Match the layout button names exactly
            if action in ['shuffle', 'next_turn']:
                if player_count > 0:
                    # Advance to the next player's turn loop
                    room.turn_index += 1

                # Pick a random question out of your prompt pool
                room.last_action_text = random.choice(ICEBREAKER_PROMPTS)
                room.save()
                return JsonResponse({'status': 'success'})

            elif action == 'end_game':
                room.status = 'FINISHED'
                room.save()
                return JsonResponse({'status': 'success'})

        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    # GET REQUEST RENDERING
    current_p = players[room.turn_index % player_count] if player_count > 0 else None
    context = {
        'room': room,
        'is_host': (room.host == request.user),
        'prompt': room.last_action_text or "Press Next Card to Break the Ice!",
        'current_player': current_p,
    }
    return render(request, 'icebreaker.html', context)


import random
import traceback
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Rooms

MOST_LIKELY_SCENARIOS = [
    "Most likely to survive a zombie apocalypse.",
    "Most likely to accidentally join a cult.",
    "Most likely to become a multi-millionaire but live like a broke student.",
    "Most likely to win a reality TV show.",
    "Most likely to get arrested for something completely accidental.",
    "Most likely to become a supervillain."
]


@login_required
def most_likely_play(request, room_code):
    """
    Isolated 'Most Likely To' engine supporting live vote changes,
    tie-detection where ALL tied players win a full point, and reset states.
    """
    room = get_object_or_404(Rooms, room_code=room_code)

    if room.status == 'FINISHED':
        return redirect('dashboard')

    players = room.players.all()

    if request.method == "POST":
        try:
            action = request.POST.get('action')

            # --- ACTION 1: VOTE CASTING ---
            if action == 'cast_vote':
                target_username = request.POST.get('target')
                turn_val = getattr(room, 'turn_index', 0)
                session_key = f"vote_{room.room_code}_{turn_val}"

                current_scores = getattr(room, 'current_scores', {}) or {}
                if not isinstance(current_scores, dict):
                    current_scores = {}

                previous_vote = request.session.get(session_key)

                if previous_vote:
                    if previous_vote == target_username:
                        return JsonResponse({'status': 'success'})

                    if previous_vote in current_scores and current_scores[previous_vote] > 0:
                        current_scores[previous_vote] -= 1

                request.session[session_key] = target_username
                request.session.modified = True

                current_scores[target_username] = current_scores.get(target_username, 0) + 1
                room.current_scores = current_scores
                room.save()

                return JsonResponse({'status': 'success'})

            # --- ACTION 2: LIVE CHAT HANDLING (GLOBAL ACCESS) ---
            elif action == 'send_chat':
                content = request.POST.get('content', '').strip()
                if content:
                    # Creates the message log record tied to the room.
                    # Verify if your model fields match (e.g. room, user, content)
                    Message.objects.create(
                        room=room,
                        user=request.user,
                        content=content
                    )
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': 'Empty message'}, status=400)

            # --- ACTION 3: HOST ACTIONS (RESTRICTED GATE) ---
            if request.user == room.host:
                if action in ['shuffle', 'next_turn']:
                    current_scores = getattr(room, 'current_scores', {}) or {}
                    celebration_text = "Nobody"

                    if current_scores:
                        highest_vote_count = max(current_scores.values())
                        winners = [user for user, count in current_scores.items() if
                                   count == highest_vote_count and count > 0]

                        if winners:
                            for winner_name in winners:
                                winning_player = room.players.filter(user__username=winner_name).first()
                                if winning_player and hasattr(winning_player, 'score'):
                                    winning_player.score += 1
                                    winning_player.save()

                            if len(winners) > 1:
                                celebration_text = "Tie! " + " & ".join(winners)
                            else:
                                celebration_text = winners[0]

                    if hasattr(room, 'current_truth_dare'):
                        room.current_truth_dare = celebration_text

                    if hasattr(room, 'turn_index'):
                        room.turn_index += 1

                    room.last_action_text = random.choice(MOST_LIKELY_SCENARIOS)
                    room.current_scores = {}
                    room.save()
                    return JsonResponse({'status': 'success'})


            elif action == 'end_game':
                for player in room.players.all():

                    if hasattr(player, 'score'):
                        player.score = 0

                        player.save()

                # 2. Clear out the current round's real-time vote tracker dict

                room.current_scores = {}
                room.status = 'FINISHED'
                room.last_action_text = "Game ended by host."
                room.save()

                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'message': 'Unauthorized action'}, status=403)

        except Exception as e:
            print("\n!!! DETECTED CRASH IN most_likely_play POST !!!")
            print(traceback.format_exc())
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    context = {
        'room': room,
        'is_host': (room.host == request.user),
        'prompt': room.last_action_text or "Press Next Round to load a scenario!",
    }
    return render(request, 'game.html', context)


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Rooms, ChatMessage  # Ensure ChatMessage is imported
import os
import uuid


@login_required
def upload_proof(request, room_code):
    if request.method != 'POST':
        return JsonResponse({'status': 'FAILED', 'error': 'Invalid request'}, status=400)

    room = get_object_or_404(Rooms, room_code=room_code)
    uploaded_file = request.FILES.get('proof_file')

    if not uploaded_file:
        return JsonResponse({'status': 'FAILED', 'error': 'No file received'}, status=400)

    try:
        # 1. Generate clean extension and unique file name
        ext = os.path.splitext(uploaded_file.name)[1] or '.webm'
        filename = f"proofs/{room_code}_{uuid.uuid4().hex[:8]}{ext}"

        # 2. Save file
        saved_path = default_storage.save(filename, ContentFile(uploaded_file.read()))
        file_url = default_storage.url(saved_path)

        # 3. Update active gameplay target state (optional)
        if hasattr(room, 'latest_proof_url'):
            room.latest_proof_url = file_url
            room.save()

        # 4. Save directly into the chat database!
        # Modify field names ('room', 'user', 'content', 'file_url') to match your exact ChatMessage model properties
        ChatMessage.objects.create(
            room=room,
            user=request.user,
            content="🎥 Sent a proof recording/file!",
            file_url=file_url  # <-- Ensure you have a 'file_url' CharField in your ChatMessage model!
        )

        return JsonResponse({
            'status': 'SUCCESS',
            'file_url': file_url
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'FAILED', 'error': str(e)}, status=500)


@login_required
def devils_poker_play(request, room_code):
    """
    Renders the game board and handles AJAX game moves.
    Tracks persistent score using Django sessions to avoid database schema alterations.
    """
    room = get_object_or_404(Rooms, room_code=room_code)
    user = request.user

    # 1. Fetch the active lobby Profile participants right now
    active_profiles = list(room.players.all())

    # Extract the underlying User model instances from the Profile objects
    p1_user = active_profiles[0].user if len(active_profiles) > 0 else None
    p2_user = active_profiles[1].user if len(active_profiles) > 1 else None

    # 2. Get or create the session using the actual User instances
    session, created = DevilsPokerSession.objects.get_or_create(
        room=room,
        defaults={
            'player1': p1_user,
            'player2': p2_user,
            'current_turn': p1_user,
        }
    )

    # --- SESSION-BASED PERSISTENT SCORE STORAGE ---
    score_key_p1 = f"poker_score_{room_code}_{session.player1.id if session.player1 else 0}"
    score_key_p2 = f"poker_score_{room_code}_{session.player2.id if session.player2 else 0}"

    if score_key_p1 not in request.session:
        request.session[score_key_p1] = 0
    if score_key_p2 not in request.session:
        request.session[score_key_p2] = 0

    # 3. AUTO-INITIALIZE PHASE (Runs ONLY when the session is first created or explicitly in SETUP)
    if created or getattr(session, 'stage', '') == 'SETUP':
        session.player1 = p1_user
        session.player2 = p2_user
        session.current_turn = p1_user
        session.winner = None

        request.session[score_key_p1] = 0
        request.session[score_key_p2] = 0

        if hasattr(session, 'stage'):
            session.stage = 'PLAYING'

        if hasattr(session, 'deal_cards'):
            session.deal_cards()

            # FORCE RE-ASSIGNMENT TO BYPASS DJANGO MUTABILITY BLOCKS
            if hasattr(session, 'player1_hand'):
                session.player1_hand = list(session.player1_hand)
                session.player2_hand = list(session.player2_hand)
                session.player1_active_indices = list(session.player1_active_indices)
                session.player2_active_indices = list(session.player2_active_indices)

        session.save()

    # 4. Enforce strict matching protection
    if user != session.player1 and user != session.player2:
        raise Http404("You are not a participant in this Devil's Poker session.")

    # Identify roles based on session data
    is_p1 = (user == session.player1)
    player_num = 1 if is_p1 else 2
    opponent_num = 2 if is_p1 else 1
    opponent = session.player2 if is_p1 else session.player1

    # --- HANDLE AJAX POST ACTIONS ---
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        action = request.POST.get("action")

        if action == "guess":
            try:
                target_index = int(request.POST.get("index"))
                already_had_winner = session.winner is not None

                result = session.make_guess(user, target_index)

                if session.winner and not already_had_winner:
                    if session.winner == session.player1:
                        request.session[score_key_p1] += 1
                    elif session.winner == session.player2:
                        request.session[score_key_p2] += 1
                    request.session.modified = True

                return JsonResponse(result)
            except (ValueError, TypeError):
                return JsonResponse({"status": "error", "message": "Invalid card selected."})

        elif action == "resolve_penalty":
            if getattr(session, 'stage', '') == 'PENALTY' and session.current_turn == user:
                session.resolve_penalty()
                return JsonResponse({"status": "success", "message": "Penalty resolved. Turn swapped."})
            return JsonResponse({"status": "error", "message": "You cannot bypass this penalty yet."})

        elif action == "next_round":
            session.winner = None
            if hasattr(session, 'stage'):
                session.stage = 'PLAYING'

            session.player1 = p1_user
            session.player2 = p2_user
            session.current_turn = p1_user

            # Trigger the deal shuffle routine
            if hasattr(session, 'deal_cards'):
                session.deal_cards()

                # CRITICAL RESHUFFLE FIX: Manually cast and re-assign lists.
                # This breaks the reference and forces Django to identify the data change,
                # ensuring the newly shuffled setup writes out to the database.
                if hasattr(session, 'player1_hand'):
                    session.player1_hand = list(session.player1_hand)
                    session.player2_hand = list(session.player2_hand)
                    session.player1_active_indices = list(session.player1_active_indices)
                    session.player2_active_indices = list(session.player2_active_indices)

            session.save()

            return JsonResponse({"status": "success", "message": "Cards reshuffled. Scores preserved."})

        return JsonResponse({"status": "error", "message": "Invalid Action."})

    # --- HANDLE AJAX GET STATE UPDATES (POLLING) ---
    if request.GET.get("format") == "json":
        my_hand = session.get_hand_list(player_num)
        my_active_indices = session.get_active_indices(player_num)
        opponent_active_indices = session.get_active_indices(opponent_num)

        masked_opponent_hand = []
        for idx in range(5):
            if idx in opponent_active_indices:
                masked_opponent_hand.append("?")
            else:
                masked_opponent_hand.append("R")

        my_score = request.session[score_key_p1] if is_p1 else request.session[score_key_p2]
        opponent_score = request.session[score_key_p2] if is_p1 else request.session[score_key_p1]

        # --- Inside your views.py: IF REQUEST.GET.GET("FORMAT") == "JSON" BLOCK ---

        # Pull or generate mock list collections if your engine returns objects/tuples
        raw_question = getattr(session, 'active_penalty_question', None)

        # Build an explicit sequence array of questions to feed the frontend stacking logic
        if raw_question:
            penalty_questions = [
                f"Question 1: {raw_question}",
                "Question 2: Explain why you targeted that specific hand slot position.",
                "Question 3: Confess a strategy secret or lie told during this matchup."
            ]
        else:
            penalty_questions = []

        # --- Inside your views.py JSON payload mapping configuration block ---

        # Determine if the opponent has already clicked the next round action button
        opponent_ready = False
        if session.winner:
            # Check if the opponent profile has marked themselves ready
            # (Update this parameter attribute according to your session model implementation)
            opponent_ready = getattr(session, f"{opponent.username}_ready", False)

        data = {
            "stage": getattr(session, 'stage', 'PLAYING'),
            "current_turn": session.current_turn.username if session.current_turn else None,
            "is_my_turn": (session.current_turn == user),
            "my_hand": my_hand,
            "my_active_indices": my_active_indices,
            "opponent_name": opponent.username if opponent else "Opponent",
            "opponent_hand": masked_opponent_hand,
            "opponent_active_indices": opponent_active_indices,
            "penalty_questions": penalty_questions,
            "winner": session.winner.username if session.winner else None,
            "opponent_ready": opponent_ready,  # <--- NEW FIELD PARAMETER FOR INTERSTITIAL BANNER SYNCING
            "my_score": my_score,
            "opponent_score": opponent_score,
        }
        return JsonResponse(data)
    # --- STANDARD PAGE RENDER ---
    context = {
        "room": room,
        "session": session,
        "opponent": opponent,
        "is_p1": is_p1,
    }
    return render(request, "devils_poker.html", context)


@login_required
def get_poker_status(request, room_code):
    """
    Dedicated AJAX polling endpoint for Devil's Poker.
    Returns real-time game states, masked hand arrays, and active penalties.
    """
    room = get_object_or_404(Rooms, room_code=room_code)
    session = DevilsPokerSession.objects.filter(room=room).first()

    if not session:
        return JsonResponse({"status": "waiting", "message": "Game session initializing..."})

    user = request.user

    # 1. Enforce participant boundary validation
    if user != session.player1 and user != session.player2:
        raise Http404("You are not part of this Devil's Poker session.")

    # 2. Determine index positions & roles
    is_p1 = (user == session.player1)
    player_num = 1 if is_p1 else 2
    opponent_num = 2 if is_p1 else 1
    opponent = session.player2 if is_p1 else session.player1

    # 3. Retrieve raw hand data and active indices from model helpers
    my_hand = session.get_hand_list(player_num) if hasattr(session, 'get_hand_list') else []
    my_active_indices = session.get_active_indices(player_num) if hasattr(session, 'get_active_indices') else []
    opponent_active_indices = session.get_active_indices(opponent_num) if hasattr(session, 'get_active_indices') else []

    # 4. Mask the opponent's card array for security (Prevents inspecting JSON payload)
    masked_opponent_hand = []
    for idx in range(5):
        if idx in opponent_active_indices:
            masked_opponent_hand.append("?")  # Hidden card values stay safe
        else:
            masked_opponent_hand.append("R")  # Eliminated Red card slot

    # 5. Build full custom response payload
    data = {
        "room_status": room.status,  # Track if game drops back to lobby
        "stage": getattr(session, 'stage', 'PLAYING'),
        "current_turn": session.current_turn.username if session.current_turn else None,
        "is_my_turn": (session.current_turn == user),

        # Player Data
        "my_hand": my_hand,  # E.g., ["R", "B", "R", "R", "R"]
        "my_active_indices": my_active_indices,  # Active remaining cards indices

        # Opponent Data
        "opponent_name": opponent.username if opponent else "Opponent",
        "opponent_hand": masked_opponent_hand,  # Secured display items
        "opponent_active_indices": opponent_active_indices,

        # Penalties & Winners
        "penalty_question": getattr(session, 'active_penalty_question', None),
        "winner": session.winner.username if session.winner else None,
    }

    return JsonResponse(data)


@login_required
def send_message2(request, room_code):  # Updated name
    """Handles submission of text or Base64 encoded audio strings into the content field."""
    if request.method == "POST":
        room = get_object_or_404(Rooms, room_code=room_code)
        content = request.POST.get('content', '')

        # Use your exact relation model hook (e.g., room.messages)
        msg = room.messages.model(room=room, user=request.user)
        msg.content = content
        msg.save()

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)