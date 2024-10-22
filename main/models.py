from django.db import models
from django.contrib.auth.models import User

class Game(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('waiting_for_player', 'Waiting for Player'),
        ('in_progress', 'In Progress'),
        ('over', 'Over'),
    ]
    
    player1 = models.ForeignKey(User, related_name='games_as_player1', on_delete=models.CASCADE)
    player2 = models.ForeignKey(User, related_name='games_as_player2', on_delete=models.CASCADE, null=True, blank=True)
    board_state = models.TextField()  
    turn = models.CharField(max_length=5, choices=[('white', 'White'), ('black', 'Black')])
    current_player = models.ForeignKey(User, related_name='games_as_current_player', on_delete=models.CASCADE, null=True, blank=True)
    is_over = models.BooleanField(default=False)
    winner = models.ForeignKey(User, related_name='games_won', on_delete=models.CASCADE, null=True, blank=True)
    result = models.CharField(max_length=10, choices=[('win', 'Win'), ('loss', 'Loss'), ('draw', 'Draw'), ('stalemate', 'Stalemate')], null=True, blank=True)
    journal_entry = models.TextField(null=True, blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting_for_player')
    moves = models.TextField(null=True, blank=True)
    moves_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Game between {self.player1.username} and {self.player2.username if self.player2 else 'Waiting for player'}"

    def set_winner(self, player):
        """ Helper method to set the winner and mark the game as over """
        self.winner = player
        self.is_over = True
        self.save()
        

        
