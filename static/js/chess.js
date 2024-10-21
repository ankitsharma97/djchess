
function resetBoard() {
    window.location.reload();  
    
}


function fetchBoardState() {
    const gameId = "{{ game.id }}";

    fetch(`/game/${gameId}/status/`)
        .then(response => response.json())
        .then(data => {
            if (data.board) {
                updateBoard(data.board);  
            }
        });
}

setInterval(fetchBoardState, 1000);

document.getElementById('move-form').onsubmit = function(e) {
    e.preventDefault(); 

    const src = document.getElementById('src').value;
    const dest = document.getElementById('dst').value;

    console.log('Source:', src, 'Destination:', dest); 

    if (!src || !dest) {
        alert('Please enter both source and destination.');
        return;
    }
 
    fetch('{% url "game_detail" game.id %}', {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ src: src, dest: dest })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => { throw new Error(errorData.error); });
        }
        return response.json();
    })
    .then(data => {
        updateBoard(data.board); 
    })
    .catch(error => alert(error.message)); 
};


function updateBoard(board) {
    for (const [square, piece] of Object.entries(board)) {
        document.getElementById(square).innerHTML = piece ? piece : '&nbsp;';
    }
}

function resignGame() {
    fetch('{% url "resign_game" game.id %}', {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.ok) {
            alert("You have resigned from the game.");
            window.location.href = '{% url "home" %}';  
        } else {
            alert("Error resigning the game.");
        }
    })
    .catch(error => console.error('Error:', error));
}