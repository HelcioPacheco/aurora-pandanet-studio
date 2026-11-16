"""Go position reconstruction, independent of network and commentary state."""
LETTERS='ABCDEFGHJKLMNOPQRSTUVWXYZ'

class IllegalMove(ValueError): pass

def coordinate(point,size):
    point=point.upper()
    if point in ('PASS','PA',''):return None
    if point[0] not in LETTERS:raise IllegalMove('Coordenada inválida')
    try:x=LETTERS.index(point[0]);y=size-int(point[1:])
    except ValueError:raise IllegalMove('Coordenada inválida')
    if not (0<=x<size and 0<=y<size):raise IllegalMove('Ponto fora do tabuleiro')
    return x,y

def neighbors(x,y,size):
    return [(a,b) for a,b in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)] if 0<=a<size and 0<=b<size]

def group(board,point,size):
    color=board[point];seen={point};todo=[point];liberties=set()
    while todo:
        for nxt in neighbors(*todo.pop(),size):
            if nxt not in board:liberties.add(nxt)
            elif board[nxt]==color and nxt not in seen:seen.add(nxt);todo.append(nxt)
    return seen,liberties

def play(board,color,point,size=19,previous=None):
    xy=coordinate(point,size)
    if xy is None:return dict(board)
    if xy in board:raise IllegalMove('Essa interseção já está ocupada.')
    updated=dict(board);updated[xy]=color
    enemy='W' if color=='B' else 'B'
    for nxt in neighbors(*xy,size):
        if updated.get(nxt)==enemy:
            stones,libs=group(updated,nxt,size)
            if not libs:
                for stone in stones:del updated[stone]
    if not group(updated,xy,size)[1]:raise IllegalMove('Lance sem liberdades.')
    if previous is not None and updated==previous:raise IllegalMove('Recaptura imediata de ko.')
    return updated

def handicap_points(count,size):
    low=3 if size>=13 else 2;high=size-1-low;mid=size//2
    corners=[(high,low),(low,high),(high,high),(low,low)]
    if not 2<=count<=9:raise IllegalMove('Handicap não suportado')
    pts=corners[:min(count,4)]
    if count in (5,7,9):pts.append((mid,mid))
    if count>=6:pts.extend([(low,mid),(high,mid)])
    if count>=8:pts.extend([(mid,low),(mid,high)])
    return pts

def reconstruct(moves,size=19,ply=None,variation=None,handicap=0,setup=None,next_color=None):
    board={tuple(p[:2]):p[2] for p in (setup or [])};previous=None;last=None;next_color=next_color or 'B';warnings=[]
    selected=moves if ply is None else moves[:max(0,ply)]
    # IGS includes a synthetic Handicap move; never place handicap twice.
    synthetic=any(str(m.get('point','')).lower()=='handicap' for m in moves)
    if handicap>=2 and not synthetic and not setup:
        board={p:'B' for p in handicap_points(handicap,size)};next_color='W'
    for move in list(selected)+list(variation or []):
        color=move['color'];point=move['point']
        if point.lower()=='handicap':
            count=int((move.get('extra') or [handicap])[0])
            board={p:'B' for p in handicap_points(count,size)};next_color='W';last=None;previous=None;continue
        old=board
        board=play(board,color,point,size,previous)
        previous=old;last=coordinate(point,size);next_color='W' if color=='B' else 'B'
    return dict(stones=[[x,y,c] for (x,y),c in board.items()],last=list(last) if last else None,
                next_color=next_color,size=size,ply=len(selected),warnings=warnings)
