from datetime import timedelta
import json
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render,redirect
from django.http import HttpResponse
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.db.models import Q 
from .models import Game
from django.contrib import messages
from django.utils.timezone import now
import chess

board = chess.Board()

# Create your views here.

@login_required
def get_active_players(request):
    ten_minutes_ago = now() - timedelta(hours=2)
    active_users = User.objects.filter(last_login__gte=ten_minutes_ago).exclude(id=request.user.id)
    players_data = [{'id': user.id, 'first_name': user.first_name} for user in active_users]
    return JsonResponse({'players': players_data})

# @login_required
# def get_active_players(request):
#     if request.user.is_authenticated:
#         players = User.objects.exclude(id=request.user.id).exclude(is_active=False)
#         players_data = [{'id': player.id, 'first_name': player.first_name} for player in players]
#         return JsonResponse({'players': players_data})
#     return JsonResponse({'error': 'User not authenticated'}, status=401)

def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    active_game = Game.objects.filter(
        (Q(player1=request.user) | Q(player2=request.user)),
        is_over=False
    ).first()

    # Retrieve past games for the current user
    past_games = Game.objects.filter(
        (Q(player1=request.user) | Q(player2=request.user)),
        is_over=True
    ).order_by('-updated_at')  
    
    players = User.objects.exclude(id=request.user.id).exclude(is_active=False)


    context = {
        'active_game': active_game,
        'past_games': past_games,
        'players': players,
        'title': 'Chess Game - Dashboard',
    }

    return render(request, 'index.html', context)


def login(request):
    if request.method == "POST":
        password = request.POST['password']
        username = request.POST['username']
        user = authenticate(username=username, password=password)
        if user:
            user.is_active = True
            auth_login(request, user)
            request.session['name'] = user.first_name
            return redirect('home')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


def signup(request):
    if request.method == "POST":
        name = request.POST['name']
        email = request.POST['email']
        password = request.POST['password']
        password1 = request.POST['password1']
        username = request.POST['username']
        if password != password1:
            return render(request, 'signup.html', {'error': 'Password does not match'})
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already exists'})
        request.session['name'] = name
        user = User.objects.create_user(username=username, email=email, password=password,first_name=name)
        user.save()
        
        return redirect('login')
    return render(request, 'signup.html',)

@login_required
def logout(request):
    user = request.user
    user.is_active = False
    auth_logout(request)
    return redirect('home')

@login_required
def passchange(request):
    user = request.user
    error = None
    if request.method == "POST":
        password = request.POST.get('password')
        npassword = request.POST.get('npassword')
        if not user.check_password(password):
            error = 'Invalid Password'
        elif password == npassword:
            error = 'New Password is the same as the old password'
        else:
            user.set_password(npassword)
            user.save()
            update_session_auth_hash(request, user)  
            return redirect('login')
    return render(request, 'updatePass.html', {
        'user': user,
        'error': error
    })
    


# chess board


@login_required
def validmove(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    board = chess.Board(game.board_state)

    if request.method == "POST":
        if game.is_over:
            return JsonResponse({'error': 'Game is already over'}, status=400)

        if (game.turn == 'white' and request.user != game.player1) or (game.turn == 'black' and request.user != game.player2):
            return JsonResponse({'error': 'It is not your turn'}, status=403)

        data = json.loads(request.body)  
        src = data.get('src')
        dest = data.get('dest')
        move = chess.Move.from_uci(src + dest)

        if move in board.legal_moves:
            board.push(move)
            game.board_state = board.fen()
            game.turn = 'black' if game.turn == 'white' else 'white'

            if board.is_checkmate():
                game.is_over = True
                game.winner = game.player1 if game.turn == 'black' else game.player2
            elif board.is_stalemate():
                game.is_over = True
                game.winner = None  # Draw condition

            game.save()
            return JsonResponse({'board': board_status(board)})  
        else:
            return JsonResponse({'error': 'Invalid Move'}, status=400)

    return JsonResponse({'board': board_status(board)})


@login_required
def create_game(request):
    if request.method == "POST":
        ongoing_games_as_player1 = request.user.games_as_player1.filter(is_over=False).exists()
        ongoing_games_as_player2 = request.user.games_as_player2.filter(is_over=False).exists()

        if ongoing_games_as_player1 or ongoing_games_as_player2:
            return render(request, 'error.html', {'error': 'You cannot start a new game until your current game is completed.'})

        invited_player_id = request.POST.get('invite_player')

        if invited_player_id:
            invited_player = User.objects.get(id=invited_player_id)
            game = Game.objects.create(
                player1=request.user,
                player2=invited_player,
                board_state=chess.Board().fen(),
                turn='white',
                status='pending'
            )
            messages.info(request, 'Game created! Waiting for the other player to join.')
        else:
            game = Game.objects.create(
                player1=request.user,
                board_state=chess.Board().fen(),
                turn='white',
                status='waiting_for_player'
            )
            messages.info(request, 'Game created! Waiting for another player to join.')

        return redirect('game_detail', game_id=game.id)

    users_to_invite = User.objects.exclude(id=request.user.id)
    return render(request, 'create_game.html', {'users_to_invite': users_to_invite})




@login_required
def join_game(request):
    if request.method == "POST":

        game_id = request.POST.get('game_id')
        game = get_object_or_404(Game, id=game_id)


        if game.player1 == request.user:
            return render(request, 'error.html', {'error': 'You cannot join a game you created.'})

        if game.status == 'pending':
            if game.player2 is None:
                game.player2 = request.user
                game.status = 'in_progress'  
                game.save() 

                messages.success(request, 'You have successfully joined the game! The game is now in progress.')
                return redirect('game_detail', game_id=game.id)
            else:
                return render(request, 'error.html', {'error': 'Game is already full.'})


        elif game.status != 'pending':
            return render(request, 'error.html', {'error': 'You cannot join this game, it is either in progress or completed.'})

    available_games = Game.objects.filter(player2__isnull=True, status='pending').exclude(player1=request.user)
    return render(request, 'join_game.html', {'games': available_games})


def board_status(board):
    board_dict = {chess.square_name(square): (board.piece_at(square).symbol() if board.piece_at(square) else None)
                  for square in chess.SQUARES}
    return board_dict

@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    
    isJoined = request.GET.get('isJoined') 
    if isJoined=='yes':
        game.status = 'in_progress'
        game.save()
        messages.success(request, 'You have successfully joined the game! The game is now in progress.')
        return redirect('game_detail', game_id=game.id)
    
    if  game.status == 'waiting_for_player' or game.status == 'pending':
        return render(request, 'waiting_for_player.html', {'game': game})

    board = chess.Board(game.board_state)

    if request.method == "POST":
        if game.is_over:
            return JsonResponse({'error': 'Game is already over'}, status=400)
        
        try:
            data = json.loads(request.body)
            src = data.get('src')
            dest = data.get('dest')

            if (game.turn == 'white' and request.user != game.player1) or (game.turn == 'black' and request.user != game.player2):
                return JsonResponse({'error': 'It is not your turn'}, status=403)

            move = chess.Move.from_uci(src + dest)

            if move in board.legal_moves:
                board.push(move)
                game.board_state = board.fen()
                

                moves = game.moves or ''
                game.moves = f'{moves} {src}{dest}'
                game.moves_count += 1

                game.turn = 'black' if board.turn == chess.BLACK else 'white'
                game.current_player = game.player2 if game.turn == 'black' else game.player1

                if board.is_checkmate():
                    game.is_over = True
                    game.winner = game.player1 if game.turn == 'black' else game.player2
                    game.result = 'win' if game.turn == 'black' else 'loss'
                elif board.is_stalemate():
                    game.is_over = True
                    game.winner = None
                    game.result = 'stalemate'
                
                game.save()
                return JsonResponse({'board': board_status(board)})
            else:
                return JsonResponse({'error': 'Invalid move'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return render(request, 'game_detail.html', {'game': game, 'board': board_status(board)})


@login_required
def resign_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    if request.method == "POST":
        if request.user == game.player1 or request.user == game.player2:
            game.is_over = True
            game.winner = game.player2 if request.user == game.player1 else game.player1  # Assign winner on resignation
            game.result = 'win' if request.user == game.player2 else 'loss'
            game.save()
            return redirect('home')
    return JsonResponse({'error': 'Unauthorized'}, status=403)



def game_status(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return JsonResponse({
        'board': board_status(chess.Board(game.board_state)),  
        'game': {
            'status': game.status
        }
    })
    
@login_required
def edit_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    
    if request.method == 'POST':
        journal_entry = request.POST.get('journal_entry')
        game.journal_entry = journal_entry  
        game.save()
        messages.success(request, 'Journal entry updated successfully!')
        return redirect('home')

    return render(request, 'edit_game.html', {'game': game})


@login_required
def delete_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    
    if request.method == 'POST':
        if game.player1 == request.user or (game.player2 and game.player2 == request.user):
            game.delete() 
            messages.success(request, 'Game deleted successfully!')
        else:
            messages.error(request, 'You do not have permission to delete this game.')
        
        return redirect('home') 
    
    return render(request, 'confirm_delete.html', {'game': game})


@login_required
def history(request):
    user = request.user
    games_as_player1 = Game.objects.filter(player1=user)
    games_as_player2 = Game.objects.filter(player2=user)
    games = games_as_player1 | games_as_player2 

    return render(request, 'history.html', {
        'games': games,
    })
    
 
@login_required
def profile(request):
    user = request.user

    total_games = Game.objects.filter(player1=user).count() + Game.objects.filter(player2=user).count()
    total_wins = Game.objects.filter(winner=user).count()
    total_losses = total_games - total_wins 

    return render(request, 'profile.html', {
        'user': user,
        'total_games': total_games,
        'total_wins': total_wins,
        'total_losses': total_losses,
    })
    


def about(request):
    return render(request, 'about.html')


