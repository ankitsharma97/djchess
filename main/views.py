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
import chess

board = chess.Board()

# Create your views here.


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

    context = {
        'active_game': active_game,
        'past_games': past_games,
        'title': 'Chess Game - Dashboard',
    }

    return render(request, 'index.html', context)


def login(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(username=email, password=password)
        if user:
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
        if password != password1:
            return render(request, 'signup.html', {'error': 'Password does not match'})
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already exists'})
        request.session['name'] = name
        user = User.objects.create_user(username=email, email=email, password=password,first_name=name)
        user.save()
        
        return redirect('login')
    return render(request, 'signup.html',)

@login_required
def logout(request):
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

        game = Game.objects.create(player1=request.user, board_state=chess.Board().fen(), turn='white')
        return redirect('game_detail', game_id=game.id)

    return render(request, 'create_game.html')


@login_required
def join_game(request):
    if request.method == "POST":
        game_id = request.POST.get('game_id')
        game = get_object_or_404(Game, id=game_id)

        if game.player1 == request.user:
            return render(request, 'error.html', {'error': 'You cannot join a game you created.'})

        if game.player2 is None:
            game.player2 = request.user
            game.save()
            return redirect('game_detail', game_id=game.id)
        else:
            return render(request, 'error.html', {'error': 'Game is already full.'})

    available_games = Game.objects.filter(player2__isnull=True)
    return render(request, 'join_game.html', {'games': available_games})


def board_status(board):
    board_dict = {chess.square_name(square): (board.piece_at(square).symbol() if board.piece_at(square) else None)
                  for square in chess.SQUARES}
    return board_dict


@login_required
def game_detail(request, game_id):
    game = get_object_or_404(Game, id=game_id)
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

            if move in board.legal_moves and game.turn == ('white' if board.turn else 'black'):
                board.push(move)
                game.board_state = board.fen()
                moves = game.moves or ''
                game.moves = f'{moves} {src}{dest}'
                game.moves_count += 1
                game.turn = 'black' if game.turn == 'white' else 'white'
                
                if board.is_checkmate():
                    game.is_over = True
                    game.winner = game.player1 if game.turn == 'black' else game.player2 
                    game.result = 'win' if game.turn == 'black' else 'loss'
                elif board.is_stalemate():
                    game.is_over = True
                    game.winner = None  # 
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
    board = chess.Board(game.board_state)
    return JsonResponse({'board': board_status(board)})


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
