from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.signup, name='signup'),
    path('home/', views.dashboard, name='dashboard'),
    path('game/<str:game_key>/', views.game_detail_view, name='game_detail'),
    path('join/', views.join_room, name='join_room'),
    path('create/', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- ROOM CORE PATHS (Ensuring unique prefix strings!) ---
    path('lobby/<str:room_code>/', views.room_lobby, name='room_lobby'),
    path('room/<str:room_code>/', views.room_session, name='room_session'),
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
    path('play/icebreaker/<str:room_code>/', views.icebreaker, name='icebreaker_play'),
    path('play/most-likely/<str:room_code>/', views.most_likely, name='most_likely_play'),
    path('room/<str:room_code>/truth-dare/', views.truth_dare_game, name='truth_dare_game'),
    path('room/<str:room_code>/results/', views.game_results, name='game_results'),
]