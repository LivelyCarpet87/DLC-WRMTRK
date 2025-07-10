import glob
import math
import sqlite3, os
import deeplabcut as dlc
import numpy as np

STEP_SIZE = 5
DB_PATH = '../data/server.db'
SQLITE3_TIMEOUT = 20
SHUFFLE=10
DLC_CFG_PAATH = os.path.abspath("../data/DLC/dlc_project_stripped/config.yaml")

def acquire_video_job():
    vidQ = None
    while vidQ is None:
        con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
        cur = con.cursor()
        vidQ = cur.execute(
            '''UPDATE videos 
                SET proc_state = "processing" 
                WHERE vidMD5=(
                    SELECT vidMD5
                    FROM videos
                    WHERE proc_state = "pending"
                    ORDER BY uploadTime ASC
                    LIMIT 1
                ) 
                RETURNING vidMD5, numInd
                ''').fetchone()
        if vidQ is not None:
            con.commit()
        con.close()
    return vidQ # vidMD5, numInd  = vidQ

def dlc_track_data_generation(vidMD5, numInd):
    video_path = os.path.abspath(f"../data/ingest/videos/{vidMD5}.mp4")
    dlc.analyze_videos(DLC_CFG_PAATH, [video_path], videotype='.mp4', save_as_csv=True,
        shuffle=SHUFFLE, destfolder='../data/intermediates', n_tracks=numInd)
    
    dlc.create_labeled_video(DLC_CFG_PAATH, [video_path], videotype='mp4', 
                            shuffle=SHUFFLE, fastmode=True, displayedbodyparts='all', 
                            displayedindividuals='all', codec='mp4v', 
                            destfolder=os.path.abspath(f"../data/intermediates"), draw_skeleton=False, color_by='bodypart', track_method='box')

def track_data_processing(vidMD5):
    memCon = sqlite3.connect(':memory:')
    memCur = memCon.cursor()

    memCur.execute('''
        CREATE TABLE labels (
            frame_num INTEGER,
            indiv TEXT,
            bodypart TEXT,
            x_pos REAL,
            y_pos REAL,
            confidence REAL,
            UNIQUE(frame_num, indiv, bodypart, x_pos, y_pos)
        )
    ''')
    memCur.execute('''
        CREATE TABLE distance_moved (
            frame_num INTEGER,
            indiv TEXT,
            bodypart TEXT,
            distance REAL,
            UNIQUE(frame_num, indiv, bodypart, distance)
        )
    ''')
    memCur.execute('''
        CREATE TABLE individual_stats (
            indiv TEXT PRIMARY KEY,
            avg_length REAL,
            avg_speed REAL
        )
    ''')

    filename = [entry for entry in os.listdir('../data/intermediates/') if entry.startswith(vidMD5) and entry.endswith('.csv')][0]
    lines = []
    with open(f'../data/intermediates/{filename}', mode='r', newline='', encoding='utf-8') as file:
        lines = file.readlines()[1:]

    data = {}

    """
    data : {
        indx: time
    """

    individuals_keys = lines[0].strip().split(',')[1:]
    parts_keys = lines[1].strip().split(',')[1:]
    numInd = len(set(individuals_keys))

    parts_list = ['head', '1/8_point', '1/4_point', '3/8_point', '1/2_point', '5/8_point', '3/4_point', '7/8_point', 'tail']
    min_frame = -1
    max_frame = -1

    for line in lines[3:]:
        entries = line.strip().split(',')
        frame_num = int(entries[0])
        for label_i in range(0,int((len(entries)-1)/3)):
            indv = individuals_keys[label_i*3+1] # get the individual of this column
            part = parts_keys[label_i*3+1] # get the bodypart of this column
            x = entries[label_i*3+1]
            y = entries[label_i*3+2]
            if len(x) > 0 and len(y) > 0:
                x = float(entries[label_i*3+1])
                y = float(entries[label_i*3+2])
            else:
                x = np.NaN
                y = np.NaN
            confidence = entries[label_i*3+3]
            if len(confidence) > 0:
                confidence = float(entries[label_i*3+3])
            else:
                confidence = np.NaN
            memCur.execute(
                "INSERT OR REPLACE INTO labels (frame_num, indiv, bodypart, x_pos, y_pos, confidence) VALUES (?, ?, ?, ?, ?, ?)", 
                (frame_num, indv, part, x, y,confidence)
            )
            memCon.commit()

    min_frame = memCur.execute("SELECT MIN(frame_num) FROM labels").fetchone()[0]
    max_frame = memCur.execute("SELECT MAX(frame_num) FROM labels").fetchone()[0]

    speed_data = []
    for indv in [f"ind{i}" for i in range(1,numInd+1)]:
        get_body_pos_never_null_query = '''
        SELECT
        head.x_pos         AS head_x,          head.y_pos         AS head_y,
        p18.x_pos          AS eighth_x,        p18.y_pos           AS eighth_y,
        p14.x_pos          AS quarter_x,       p14.y_pos           AS quarter_y,
        p38.x_pos          AS three_eighths_x, p38.y_pos           AS three_eighths_y,
        p12.x_pos          AS half_x,          p12.y_pos           AS half_y,
        p58.x_pos          AS five_eighths_x,  p58.y_pos           AS five_eighths_y,
        p34.x_pos          AS three_quarters_x,p34.y_pos           AS three_quarters_y,
        p78.x_pos          AS seven_eighths_x, p78.y_pos           AS seven_eighths_y,
        tail.x_pos         AS tail_x,          tail.y_pos          AS tail_y
        FROM labels AS head
        JOIN labels AS p18 ON p18.frame_num = head.frame_num AND p18.indiv = head.indiv AND p18.bodypart = '1/8_point' AND p18.x_pos IS NOT NULL AND p18.x_pos = p18.x_pos AND p18.y_pos IS NOT NULL AND p18.y_pos = p18.y_pos
        JOIN labels AS p14 ON p14.frame_num = head.frame_num AND p14.indiv = head.indiv AND p14.bodypart = '1/4_point' AND p14.x_pos IS NOT NULL AND p14.x_pos = p14.x_pos AND p14.y_pos IS NOT NULL AND p14.y_pos = p14.y_pos
        JOIN labels AS p38 ON p38.frame_num = head.frame_num AND p38.indiv = head.indiv AND p38.bodypart = '3/8_point' AND p38.x_pos IS NOT NULL AND p38.x_pos = p38.x_pos AND p38.y_pos IS NOT NULL AND p38.y_pos = p38.y_pos
        JOIN labels AS p12 ON p12.frame_num = head.frame_num AND p12.indiv = head.indiv AND p12.bodypart = '1/2_point' AND p12.x_pos IS NOT NULL AND p12.x_pos = p12.x_pos AND p12.y_pos IS NOT NULL AND p12.y_pos = p12.y_pos
        JOIN labels AS p58 ON p58.frame_num = head.frame_num AND p58.indiv = head.indiv AND p58.bodypart = '5/8_point' AND p58.x_pos IS NOT NULL AND p58.x_pos = p58.x_pos AND p58.y_pos IS NOT NULL AND p58.y_pos = p58.y_pos
        JOIN labels AS p34 ON p34.frame_num = head.frame_num AND p34.indiv = head.indiv AND p34.bodypart = '3/4_point' AND p34.x_pos IS NOT NULL AND p34.x_pos = p34.x_pos AND p34.y_pos IS NOT NULL AND p34.y_pos = p34.y_pos
        JOIN labels AS p78 ON p78.frame_num = head.frame_num AND p78.indiv = head.indiv AND p78.bodypart = '7/8_point' AND p78.x_pos IS NOT NULL AND p78.x_pos = p78.x_pos AND p78.y_pos IS NOT NULL AND p78.y_pos = p78.y_pos
        JOIN labels AS tail ON tail.frame_num = head.frame_num AND tail.indiv = head.indiv AND tail.bodypart = 'tail' AND tail.x_pos IS NOT NULL AND tail.x_pos = tail.x_pos AND tail.y_pos IS NOT NULL AND tail.y_pos = tail.y_pos
        WHERE
        head.bodypart = 'head' AND
        head.indiv = ? AND
        head.x_pos IS NOT NULL AND head.x_pos = head.x_pos AND
        head.y_pos IS NOT NULL AND head.y_pos = head.y_pos;
        '''
        points = [
            ("head_x", "head_y"),
            ("eighth_x", "eighth_y"),
            ("quarter_x", "quarter_y"),
            ("three_eighths_x", "three_eighths_y"),
            ("half_x", "half_y"),
            ("five_eighths_x", "five_eighths_y"),
            ("three_quarters_x", "three_quarters_y"),
            ("seven_eighths_x", "seven_eighths_y"),
            ("tail_x", "tail_y")
        ]
        memCur.execute(get_body_pos_never_null_query, (indv,))
        rows = memCur.fetchall()

        lengths = []
        for row in rows:
            length = 0.0
            for i in range(len(points) - 1):
                x1, y1 = row[2 * i], row[2 * i + 1]
                x2, y2 = row[2 * (i + 1)], row[2 * (i + 1) + 1]
                length += math.hypot(x1, y1, x2, y2)
            lengths.append(length)
        
        indv_len = np.median(lengths)
        data = []
        for frame_ind in range(min_frame+STEP_SIZE,max_frame+1,STEP_SIZE):
            entry = []
            for bodypart in parts_list[1:-1]: # Ignore ends of the worms
                x_pos_prev = np.NaN
                y_pos_prev = np.NaN
                prev_q = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', (frame_ind-STEP_SIZE, indv, bodypart) ).fetchone()
                if prev_q is not None:
                    x_pos_prev = prev_q[0]
                    y_pos_prev = prev_q[1]
                x_pos_now = np.NaN
                y_pos_now = np.NaN
                now_q = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', (frame_ind, indv, bodypart) ).fetchone()
                if now_q is not None:
                    x_pos_now = now_q[0]
                    y_pos_now = now_q[1]
                if None in [x_pos_prev, y_pos_prev, x_pos_now, y_pos_now]:
                    distance = np.NaN
                else:
                    distance = math.hypot(x_pos_now - x_pos_prev, y_pos_now - y_pos_prev)
                if distance > indv_len/8*2:
                    distance = np.NaN
                entry.append(distance)
            if np.isnan(np.array(entry)).sum() == len(entry):
                break
            data.append(entry)
        
        speed = np.nanmean(np.array(data))/STEP_SIZE
        if np.isnan(speed):
            raise ValueError
        elif memCur.execute('SELECT AVG(confidence) from labels WHERE indiv = ?', [indv]).fetchone()[0] < 0.60:
            raise ValueError
        elif len(data) < len(range(min_frame+STEP_SIZE,max_frame+1,STEP_SIZE))/8:
            raise ValueError
        confidence = True
        if np.isnan(np.array(data)).sum() > len(data)/4 or len(data) < len(range(min_frame+STEP_SIZE,max_frame+1,STEP_SIZE))/2:
            confidence = False
        elif memCur.execute('SELECT AVG(confidence) from labels WHERE indiv = ?', [indv]).fetchone()[0] < 0.80:
            confidence = False
        speed_data.append( (indv,speed,confidence) )
    
    for v in speed_data:
        indv,speed,confidence = v
        con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
        cur = con.cursor()
        cur.execute("INSERT OR REPLACE INTO detectedIndv(vidMD5, ind, speed, confidence) VALUES(?,?,?,?)",
                    [vidMD5,indv,speed,confidence])
        con.commit()
        con.close()


def mark_complete(vidMD5):
    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    cur.execute("UPDATE videos SET proc_state = 'done' WHERE vidMD5 = ?", [vidMD5])
    con.commit()
    con.close()

def mark_warning(vidMD5):
    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    cur.execute("UPDATE videos SET proc_state = 'warning' WHERE vidMD5 = ?", [vidMD5])
    con.commit()
    con.close()

def mark_failed(vidMD5):
    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    cur.execute("UPDATE videos SET proc_state = 'failed' WHERE vidMD5 = ?", [vidMD5])
    con.commit()
    con.close()

def cleanup(vidMD5):
    labeled_video_q = [entry for entry in os.listdir('../data/intermediates/') if entry.startswith(vidMD5) and entry.endswith('.mp4')]
    if len(labeled_video_q) > 0:
        labeled_video = labeled_video_q[0]
        os.rename(f'../data/intermediates/{labeled_video}', f'../data/outputs/{vidMD5}_labeled.mp4')
    purgelist = [f'../data/intermediates/{entry}' for entry in os.listdir('../data/intermediates/') if entry.startswith(vidMD5)]
    for item in purgelist:
        os.remove(item)

while True:
    vidMD5, numInd = acquire_video_job()
    print(f'Found job: {vidMD5}')
    try:
        for attempt in range(3):
            try:
                if attempt == 0:
                    dlc_track_data_generation(vidMD5, numInd)
                elif attempt == 1:
                    if numInd - 1 < 1:
                        raise ValueError
                    dlc_track_data_generation(vidMD5, numInd-1)
                elif attempt == 2:
                    dlc_track_data_generation(vidMD5, numInd+1)
                
                track_data_processing(vidMD5)
                if attempt == 0:
                    mark_complete(vidMD5)
                else:
                    mark_warning(vidMD5)
                break
            except ValueError:
                print("detector failed")
                cleanup(vidMD5)
                if attempt == 2:
                    mark_failed(vidMD5)
                    raise ValueError
            except OSError:
                mark_failed(vidMD5)
                print("detector failed")
                cleanup(vidMD5)
                if attempt == 2:
                    mark_failed(vidMD5)
                    raise ValueError
    except ValueError:
        mark_failed(vidMD5)
    cleanup(vidMD5)

    