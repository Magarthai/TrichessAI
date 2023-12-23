import asyncio
import websockets
from message import MOVABLE, LEGALMOVE,SELECT_MOVE,ENEMY_MOVE,KINGMOVE,DODGE
import random
import json
import sys
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

json_decoder = json.loads

board_data = {}

import random

def select_move_from_processed_board(processed_board):
    capture_moves = []
    other_moves = []

    for move in processed_board['legal_moves']:
        capture_moves.append(move)

    if capture_moves:
        # Group capture moves by their priority
        capture_moves_by_priority = group_moves_by_priority(capture_moves)
        highest_priority = max(capture_moves_by_priority.keys())
        return random.choice(capture_moves_by_priority[highest_priority])
    elif other_moves:
        other_moves_by_priority = group_moves_by_priority(other_moves)
        highest_priority = max(other_moves_by_priority.keys())
        return random.choice(other_moves_by_priority[highest_priority])

    return None

def group_moves_by_priority(moves):
    moves_by_priority = {}
    for move in moves:
        priority = move[3]
        if priority not in moves_by_priority:
            moves_by_priority[priority] = []
        moves_by_priority[priority].append(move)
    return moves_by_priority


player_number = input("Enter a number: ")
player_number = f"Player{player_number}"
print("Now you are",player_number)
async def connect():
    uri = "ws://192.168.2.54:8181/game"
    async with websockets.connect(uri) as websocket:
        print(f'Connecting to {uri}')

        
        await websocket.send(json.dumps({"Command": "Join"}))
        response = await websocket.recv()
        password = json.loads(response).get("Password", "")
        print(f'Password received from server: {password}')


        while True:
            await websocket.send(json.dumps({"Command": "CheckTurn", "Password": password}))
            status_response = await websocket.recv()
            corrected_status_response = status_response.replace('True', 'true').replace('False', 'false')
            status_data = json.loads(corrected_status_response)

            if status_data.get("Status") == "Success" and status_data.get("YourTurn"):
                board_list = status_data["Board"]
                movable_fields = await fetch_movable_fields(board_list, player_number, password, websocket)
                print(MOVABLE.encode('utf-8', errors='replace').decode('utf-8'))
                print(movable_fields)
                enemy_movable_fields = await fetch_enemy_movable_fields(board_list, player_number, password, websocket)
                print(ENEMY_MOVE)
                print(enemy_movable_fields)
                processed_board,king_pos = process_board(board_list, player_number, movable_fields,enemy_movable_fields)
                print("King position:", king_pos)
                king_check_command = {
                        "Command": "CheckKing",
                        "Password": password,
                    }

                await websocket.send(json.dumps(king_check_command))
                king_check_response = await websocket.recv()
                king_check_data = json.loads(king_check_response.replace('True', 'true').replace('False', 'false'))
        
                print("King position:", king_pos)
                king_check_command = {
                        "Command": "CheckKing",
                        "Password": password,
                    }

                await websocket.send(json.dumps(king_check_command))
                king_check_response = await websocket.recv()
                king_check_data = json.loads(king_check_response.replace('True', 'true').replace('False', 'false'))
                await asyncio.sleep(1)
                if king_check_data.get("KingInCheck"):
                    king_movable_fields = [field['Field'] for field in king_check_data['KingMovableField']]
                    safe_king_moves = [field for field in king_movable_fields if field not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}]

                    if safe_king_moves:
                        selected_field = random.choice(safe_king_moves)
                        king_move_command = {
                            "Command": "Move",
                            "Password": password,
                            "Move": {"From": king_pos, "To": selected_field}
                        }
                        await websocket.send(json.dumps(king_move_command))
                        print(DODGE)
                        print("King moved to:", selected_field)
                    else:
                        print("No safe moves available to escape the check.")

                selected_move = select_move_from_processed_board(processed_board)
                print(SELECT_MOVE.encode('utf-8', errors='replace').decode('utf-8'))
                print(selected_move)

                if selected_move:
                    move_command = {
                        "Command": "Move",
                        "Password": password,
                        "Move": {"From": selected_move[0], "To": selected_move[1]}
                    }
                    print("Sending move command:", json.dumps(move_command))
                    await websocket.send(json.dumps(move_command))
                    status_response = await websocket.recv()
                    print("Response to move:", status_response)
                    promote_command = {
                        "Command": "Promote",
                        "Password": password,
                        "Promotion": "Queen"
                    }
                    await websocket.send(json.dumps(promote_command))
                    a = await websocket.recv()
                    a = a.replace('True', 'true').replace('False', 'false')
                    a = json.loads(a)
                    print(a)
                
                else:
                    await websocket.send(json.dumps({"Command": "CheckTurn", "Password": password}))
                    status_response = await websocket.recv()
                    corrected_status_response = status_response.replace('True', 'true').replace('False', 'false')
                    status_data = json.loads(corrected_status_response)
                    print("No legal moves available then pass")
                    pass_command = {
                    "Command": "PassTurn",
                    "Password": password
                    }
                    await websocket.send(json.dumps(pass_command))
                    a = await websocket.recv()
                    a = a.replace('True', 'true').replace('False', 'false')
                    a = json.loads(a)
            else:
                print("Waiting for game to start or for your turn...")
                await websocket.send(json.dumps({"Command": "CheckTurn", "Password": password}))
                status_response = await websocket.recv()
                corrected_status_response = status_response.replace('True', 'true').replace('False', 'false')
                status_data = json.loads(corrected_status_response)
                await asyncio.sleep(1)

async def fetch_movable_fields(board_list, player_number, password, websocket):
    movable_fields = {}
    for piece in board_list:
        field = piece['Field']
        if piece['Owner'] == player_number:
            movable_command = {
                "Command": "Movable",
                "Password": password,
                "Field": field
            }
            await websocket.send(json.dumps(movable_command))
            response = await websocket.recv()
            corrected_response = response.replace('True', 'true').replace('False', 'false')
            movable_response = json.loads(corrected_response)
            movable_fields[field] = [move['Field'] for move in movable_response.get("MovableFields", [])]
    return movable_fields

async def fetch_enemy_movable_fields(board_list, player_number, password, websocket):
    movable_fields = {}
    for piece in board_list:
        field = piece['Field']
        if piece['Owner'] != player_number:
            movable_command = {
                "Command": "Movable",
                "Password": password,
                "Field": field
            }
            await websocket.send(json.dumps(movable_command))
            response = await websocket.recv()
            corrected_response = response.replace('True', 'true').replace('False', 'false')
            movable_response = json.loads(corrected_response)
            movable_fields[field] = [move['Field'] for move in movable_response.get("MovableFields", [])]
    return movable_fields

def process_board(board_list, player_number,movable_fields,enemy_movable_fields):
    info = {
        "legal_moves": [],
        "is_in_check": False,
        "pieces_attacking_king": [],
    }
    board_data = {piece['Field']: piece for piece in board_list}

    # Find the king's position
    king_pos = None
    for square, piece_info in board_data.items():
        if piece_info.get("Piece", "").upper() == "KING" and player_number == piece_info.get("Owner", ""):
            king_pos = square
            break

    if not king_pos:
        print(f"Could not find king on the board for {player_number}")
        return info


    # Loop through all squares and analyze pieces
    for square, piece_info in board_data.items():
        piece = piece_info.get("Piece", "")
        piece_owner = piece_info.get("Owner", "")

        # Skip empty squares or opponent pieces
        if not piece or piece_owner != player_number:
            continue

        piece_type = piece.upper()
        # Generate legal moves for each piece type
        legal_moves_for_piece = []
        if piece_type == "PAWN":
            legal_moves_for_piece = validate_pawn_move(board_data, square, player_number,movable_fields,enemy_movable_fields)
        elif piece_type == "ROOK":
            legal_moves_for_piece = validate_rook_move(board_data, square,player_number,movable_fields,enemy_movable_fields)
        elif piece_type == "KNIGHT":
            legal_moves_for_piece = validate_knight_move(board_data, square,player_number,movable_fields,enemy_movable_fields)
        elif piece_type == "BISHOP":
            legal_moves_for_piece = validate_bishop_move(board_data, square,player_number,movable_fields,enemy_movable_fields)
        elif piece_type == "QUEEN":
            legal_moves_for_piece = validate_queen_move(board_data, square,player_number,movable_fields,enemy_movable_fields)
        elif piece_type == "KING":
            legal_moves_for_piece = validate_king_move(board_data, square,player_number,movable_fields,enemy_movable_fields)

        # Update legal moves and check for check
        info["legal_moves"].extend(legal_moves_for_piece)
        if square in legal_moves_for_piece and square == king_pos:
            info["is_in_check"] = True
            info["pieces_attacking_king"].append((square, piece_info))
    print(LEGALMOVE)
    print(info)
    return info,king_pos


def validate_pawn_move(board, square, player_number, movable_fields, enemy_movable_fields):
    moves = []
    piece_values = {"pawn": 50, "queen": 120, "knight": 110, "rook": 110, "bishop": 105, "king": 150}

    player1_beware = ['GA4', 'GB4', 'GC4', 'GD4', 'GE4', 'GF4', 'GG4', 'GH4', 'RH4', 'RG4', 'RF4', 'RE4', 'RD4', 'RC4', 'RB4', 'RA4']
    player2_beware = ['BA4', 'BB4', 'BC4', 'BD4', 'BE4', 'BF4', 'BG4', 'BH4', 'RH4', 'RG4', 'RF4', 'RE4', 'RD4', 'RC4', 'RB4', 'RA4']
    player3_beware = ['GA4', 'GB4', 'GC4', 'GD4', 'GE4', 'GF4', 'GG4', 'GH4', 'BA4', 'BB4', 'BC4', 'BD4', 'BE4', 'BF4', 'BG4', 'BH4']
    beware_list = player1_beware if player_number == "Player1" else (player2_beware if player_number == "Player2" else player3_beware)



    # Normal move validation if not under direct threat or no safe move available
    for move_square in movable_fields.get(square, []):
        is_enemy_reachable = any(move_square in enemy_moves for enemy_moves in enemy_movable_fields.values())
        priority = 5  # Default priority

        if move_square in board and board[move_square]["Owner"] != player_number:
            captured_piece = board[move_square]["Piece"].lower()
            priority += piece_values.get(captured_piece, 1) - 1  # Increase based on piece value
            if is_enemy_reachable:
                priority -= 10  # Reduce priority significantly if the move is reachable by an enemy
            moves.append((square, move_square, "capture", priority))
        else:
            if move_square in beware_list:
                priority -= 2  # Slightly higher priority for non-capture moves to beware columns
            moves.append((square, move_square, "nocapture", priority))

    return moves




    
def validate_rook_move(board, square, player_number, movable_fields, enemy_movable_fields):
    moves = []
    piece_values = {"pawn": 2, "queen": 115, "knight": 100, "rook": 110, "bishop": 100, "king": 150}

    is_piece_under_threat = square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}
    enemy_pieces_threatening = {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves if move == square}

    # Normal move validation
    for move_square in movable_fields.get(square, []):
        is_enemy_reachable = any(move_square in enemy_moves for enemy_moves in enemy_movable_fields.values())
        priority = 4  # Default priority

        # Capture enemy piece if it's threatening the rook
        if move_square in enemy_pieces_threatening:
            captured_piece = board[move_square]["Piece"].lower()
            priority += piece_values.get(captured_piece, 100)  # Higher priority to capture threatening piece
            moves.append((square, move_square, "capture", priority))
            continue

        # Check if the move is reachable by an enemy
        if is_enemy_reachable:
            priority -= 100  # Reduce priority if the move is reachable by an enemy

        # Process move based on whether it's a capture or a non-capture
        if move_square in board and board[move_square]["Owner"] != player_number:
            captured_piece = board[move_square]["Piece"].lower()
            priority += piece_values.get(captured_piece, 1) - 1
            moves.append((square, move_square, "capture", priority))
        else:
            moves.append((square, move_square, "nocapture", priority))

    # If rook is under direct threat and no capturing moves are available, find a safe move
    if is_piece_under_threat and not any(move[2] == "capture" for move in moves):
        safe_moves = [(square,move_square, "safe_move", 50) for move_square in movable_fields[square] if move_square not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}]
        if safe_moves:
            print(DODGE)
            for move in safe_moves:
                print("Dodge", square, "from")
                print(square, safe_moves)
            return safe_moves

    return moves




def validate_knight_move(board, square, player_number, movable_fields, enemy_movable_fields):
    moves = []
    piece_values = {"pawn": 5, "queen": 98, "knight": 12, "rook": 12, "bishop": 10, "king": 150}
    is_piece_under_threat = square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}

    for move_square in movable_fields.get(square, []):
        if move_square in board and board[move_square]["Owner"] != player_number:
            # Check if the move is a capture move and if the piece is threatened
            if is_piece_under_threat and move_square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
                # Priority to capture an enemy threatening the knight
                priority = 100 + piece_values.get(board[move_square]["Piece"].lower(), 1)
                print("Counter-Attack", square, "to", move_square)
                moves.append((square, move_square, "capture", priority))
            else:
                # Regular capture move
                priority = piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
        elif not is_piece_under_threat or move_square not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
            # Safe move or regular non-capture move
            priority = 4 - 100 * any(move_square in enemy_moves for enemy_moves in enemy_movable_fields.values())
            moves.append((square, move_square, "nocapture", priority))
    if is_piece_under_threat and not any(move[2] == "capture" for move in moves):
        safe_moves = [(square,move_square, "safe_move", 50) for move_square in movable_fields[square] if move_square not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}]
        if safe_moves:
            print(DODGE)
            for move in safe_moves:
                print("Dodge", square, "from")
                print(square, safe_moves)
            return safe_moves
    return moves



def validate_bishop_move(board, square, player_number, movable_fields, enemy_movable_fields):
    moves = []
    piece_values = {"pawn": 4, "queen": 99, "knight": 12, "rook": 13, "bishop": 12, "king": 150}
    is_piece_under_threat = square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}

    for move_square in movable_fields.get(square, []):
        if move_square in board and board[move_square]["Owner"] != player_number:
            if is_piece_under_threat and move_square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
                print("Counter-Attack", square, "to", move_square)
                priority = 100 + piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
            else:
                priority = piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
        elif not is_piece_under_threat or move_square not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
            priority = 3 - 100 * any(move_square in enemy_moves for enemy_moves in enemy_movable_fields.values())
            moves.append((square, move_square, "nocapture", priority))

    return moves



def validate_queen_move(board, square, player_number, movable_fields, enemy_movable_fields):
    moves = []
    piece_values = {"pawn": 1, "queen": 94, "knight": 10, "rook": 80, "bishop": 10, "king": 150}
    is_piece_under_threat = square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}

    for move_square in movable_fields.get(square, []):
        # Check if moving to an occupied square
        if move_square in board and board[move_square]["Owner"] != player_number:
            # If the piece is under threat and can capture the threatening piece, prioritize this move
            if is_piece_under_threat and move_square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
                print("Counter-attack: Capture threat at", move_square)
                priority = 200 + piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
            else:
                # Normal capture move
                priority = piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
        else:
            # Non-capture moves
            priority = 2 - 100 * any(move_square in enemy_moves for enemy_moves in enemy_movable_fields.values())
            moves.append((square, move_square, "nocapture", priority))
    if is_piece_under_threat and not any(move[2] == "capture" for move in moves):
        safe_moves = [(square,move_square, "safe_move", 60) for move_square in movable_fields[square] if move_square not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}]
        if safe_moves:
            print(DODGE)
            for move in safe_moves:
                print("Dodge", square, "from")
                print(square, safe_moves)
            return safe_moves
    return moves




def validate_king_move(board, square, player_number, movable_fields, enemy_movable_fields):
    moves = []
    piece_values = {"pawn": 500, "queen": 500, "knight": 500, "rook": 500, "bishop": 500, "king": 500}
    is_piece_under_threat = square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}

    for move_square in movable_fields.get(square, []):
        if move_square in board and board[move_square]["Owner"] != player_number:
            if is_piece_under_threat and move_square in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
                print("Counter-Attack", square, "to", move_square)
                priority = 1000 + piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
            else:
                priority = piece_values.get(board[move_square]["Piece"].lower(), 1)
                moves.append((square, move_square, "capture", priority))
        elif not is_piece_under_threat or move_square not in {move for enemy_moves in enemy_movable_fields.values() for move in enemy_moves}:
            priority = -100000 * any(move_square in enemy_moves for enemy_moves in enemy_movable_fields.values())
            moves.append((square, move_square, "nocapture", priority))
    
    return moves



asyncio.run(connect())


