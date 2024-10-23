from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('get_active_players/', views.get_active_players, name='get_active_players'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('passchange/', views.passchange, name='passchange'),
    path('validmove/', views.validmove, name='validmove'),
    path('new_game/', views.create_game, name='create_game'),
    path('join_game/', views.join_game, name='join_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),  
    path('game/<int:game_id>/resign/', views.resign_game, name='resign_game'),  
    path('game/<int:game_id>/status/', views.game_status, name='game_status'),
    path('edit_game/<int:game_id>/', views.edit_game, name='edit_game'),
    path('delete_game/<int:game_id>/', views.delete_game, name='delete_game'),
    path('history/', views.history, name='history'),
    path('profile/', views.profile, name='profile'),
    path('about/', views.about, name='about'),
    
]
