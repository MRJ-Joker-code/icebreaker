from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.signup, name='signup'),
    path('home/', views.dashboard, name='dashboard'),
    path('game/<str:game_key>/', views.game_detail_view, name='game_detail'),
    path('join/', views.join_room, name='join_room'),
    path('create/<str:game_key>/', views.create_room, name='create_room'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- ROOM CORE PATHS (Ensuring unique prefix strings!) ---
    path('lobby/<str:room_code>/', views.room_lobby, name='room_lobby'),
    path('start/<str:room_code>/', views.start_game, name='start_game'),
    path('room/<str:room_code>/end/', views.end_game, name='end_game'),

    # --- CREATION LOGIC ---
    path('create-room/<str:game_key>/', views.create_room, name='create_room'),
    path('create-room-by-key/<str:game_key>/', views.create_room, name='create_room_by_key'),

    # --- BACKGROUND DATA SYNC PORTS ---
    path('status/<str:room_code>/', views.get_room_status, name='get_room_status'),
    path('chat/send/<str:room_code>/', views.send_message, name='send_message'),
    path('chat/get/<str:room_code>/', views.get_messages, name='get_messages'),

    # --- GAME ENGINE REDIRECT PLUGINS ---

    path('room/<str:room_code>/results/', views.game_results, name='game_results'),
    # game/urls.py
    path('play/truth-or-dare/<str:room_code>/', views.truth_dare_play, name='truth_or_dare_play'),
    path('play/most-likely/<str:room_code>/', views.most_likely_play, name='most_likely_play'),
    path('play/icebreaker/<str:room_code>/', views.icebreaker_play, name='icebreaker_play'),


    #path('status/most-likely/<str:room_code>/', views.most_likely_status, name='most_likely_status'),
    path('room/<str:room_code>/truth-dare-status/', views.get_truth_dare_status, name='get_truth_dare_status'),
    path('play/truth-or-dare/<str:room_code>/upload/', views.upload_proof, name='upload_proof'),
    path('play/truth-or-dare/<str:room_code>/vote/', views.submit_vote, name='submit_vote'),

    path('room/<str:room_code>/poker/status/', views.get_poker_status, name='get_poker_status'),

    path('room/<str:room_code>/poker/', views.devils_poker_play, name='devils_poker_play'),
    path('room/<str:room_code>/messages/send2/', views.send_message2, name='send_message2'),
# game/urls.py
    path('room/<str:room_code>/messages/', views.get_messages, name='get_messages'),
    path('room/<str:room_code>/messages/send2/', views.send_message2, name='send_message2'),


]