#!/usr/bin/python3
import math
import sqlite3, os
import deeplabcut as dlc
import numpy as np
import cv2
import torch

torch.backends.nnpack.enabled = False

DB_PATH = '../data/server.db'
SQLITE3_TIMEOUT = 20
SHUFFLE=1
DLC_CFG_PATH = os.path.abspath("../data/DLC/dlc_project_stripped/config.yaml")
STEP_TIME = 0.1

con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
cur = con.cursor()
cur.execute('UPDATE videos SET proc_state = "pending" WHERE proc_state = "processing"')
con.commit()
con.close()

purgelist = [f'../data/intermediates/{entry}' for entry in os.listdir('../data/intermediates/') if entry != '.gitignore']
for item in purgelist:
    os.remove(item)

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
    dlc.analyze_videos(DLC_CFG_PATH, [video_path], videotype='.mp4', save_as_csv=True, use_shelve=False,
        shuffle=SHUFFLE, destfolder='../data/intermediates', n_tracks=numInd)
    
    """
    dlc.create_labeled_video(DLC_CFG_PATH, [video_path], videotype='mp4', 
                            shuffle=SHUFFLE, fastmode=True, displayedbodyparts='all', 
                            displayedindividuals='all', codec='mp4v', 
                            destfolder=os.path.abspath(f"../data/intermediates"), draw_skeleton=False, color_by='bodypart', track_method='box')
    """

def track_data_processing(vidMD5):
    print(f"Post processing {vidMD5}")
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
        # Calc len
        print(f"Calculating length of {indv} for {vidMD5}")
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
        JOIN labels AS p18 ON p18.frame_num = head.frame_num AND p18.indiv = head.indiv AND p18.bodypart = '1/8_point' AND p18.x_pos IS NOT NULL AND p18.y_pos IS NOT NULL
        JOIN labels AS p14 ON p14.frame_num = head.frame_num AND p14.indiv = head.indiv AND p14.bodypart = '1/4_point' AND p14.x_pos IS NOT NULL AND p14.y_pos IS NOT NULL
        JOIN labels AS p38 ON p38.frame_num = head.frame_num AND p38.indiv = head.indiv AND p38.bodypart = '3/8_point' AND p38.x_pos IS NOT NULL AND p38.y_pos IS NOT NULL
        JOIN labels AS p12 ON p12.frame_num = head.frame_num AND p12.indiv = head.indiv AND p12.bodypart = '1/2_point' AND p12.x_pos IS NOT NULL AND p12.y_pos IS NOT NULL
        JOIN labels AS p58 ON p58.frame_num = head.frame_num AND p58.indiv = head.indiv AND p58.bodypart = '5/8_point' AND p58.x_pos IS NOT NULL AND p58.y_pos IS NOT NULL
        JOIN labels AS p34 ON p34.frame_num = head.frame_num AND p34.indiv = head.indiv AND p34.bodypart = '3/4_point' AND p34.x_pos IS NOT NULL AND p34.y_pos IS NOT NULL
        JOIN labels AS p78 ON p78.frame_num = head.frame_num AND p78.indiv = head.indiv AND p78.bodypart = '7/8_point' AND p78.x_pos IS NOT NULL AND p78.y_pos IS NOT NULL
        JOIN labels AS tail ON tail.frame_num = head.frame_num AND tail.indiv = head.indiv AND tail.bodypart = 'tail' AND tail.x_pos IS NOT NULL AND tail.y_pos IS NOT NULL
        WHERE
        head.bodypart = 'head' AND
        head.indiv = ? AND
        head.x_pos IS NOT NULL AND head.x_pos = head.x_pos AND
        head.y_pos IS NOT NULL AND head.y_pos = head.y_pos;
        '''
        points = [
            "head",
            "p18",
            "p14",
            "p38",
            "p12",
            "p58",
            "p34",
            "p78",
            "tail"
        ]
        memCur.execute(get_body_pos_never_null_query, (indv,))
        rows = memCur.fetchall()

        lengths = []
        for row in rows:
            length = 0.0
            for i in range(len(points) - 1):
                x1, y1 = row[2 * i], row[2 * i + 1]
                x2, y2 = row[2 * (i + 1)], row[2 * (i + 1) + 1]
                length += math.hypot( x1 - x2, y1 - y2)
            if not np.isnan(length):
                lengths.append(length)
        if len(lengths) == 0:
            print(f"Unable to acquire median length for {indv} of {vidMD5}")
            continue
        indv_len = np.median(lengths)

        seg_len = indv_len / (len(points)-1)

        """
        # unflip points
        for frame_ind in range(min_frame,max_frame):
            for px in range(int(len(points)/2)):
                p1 = points[px]
                p2 = points[len(points)-px-1]
                
                p1t0Q = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p1, indv]).fetchone()
                p2t0Q = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p2, indv]).fetchone()
                p1t1Q = memCur.execute(f"SELECT x_pos, y_pos, confidence FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind+1, p1, indv]).fetchone()
                p2t1Q = memCur.execute(f"SELECT x_pos, y_pos, confidence FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind+1, p2, indv]).fetchone()

                if not (p1t0Q and p2t0Q and None not in p1t0Q and None not in p2t0Q):
                    continue

                p1t0_x, p1t0_y = p1t0Q
                p2t0_x, p2t0_y = p2t0Q

                if p1t1Q and p2t1Q and None not in p1t1Q and None not in p2t1Q:
                    p1t1_x, p1t1_y, p1t1_conf = p1t1Q
                    p2t1_x, p2t1_y, p2t1_conf = p2t1Q
                    if (math.hypot(p1t0_x, p1t0_y, p1t1_x, p1t1_y) > 0.5 * seg_len) \
                    and (math.hypot(p1t0_x, p1t0_y, p2t1_x, p2t1_y) < 0.5 * seg_len) \
                    and (math.hypot(p2t0_x, p2t0_y, p2t1_x, p2t1_y) > 0.5 * seg_len) \
                    and (math.hypot(p2t0_x, p2t0_y, p1t1_x, p1t1_y) < 0.5 * seg_len):
                        memCur.execute(f"UPDATE labels SET(x_pos, y_pos, confidence) VALUES(?,?,?) WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [p2t1_x,p2t1_y,p2t1_conf,frame_ind+1, p1, indv])
                        memCur.execute(f"UPDATE labels SET(x_pos, y_pos, confidence) VALUES(?,?,?) WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [p1t1_x,p1t1_y,p1t1_conf,frame_ind+1, p2, indv])
                        memCon.commit()
                elif p1t1Q and None not in p1t1Q:
                    p1t1_x, p1t1_y, p1t1_conf = p1t1Q
                    if (math.hypot(p1t0_x, p1t0_y, p1t1_x, p1t1_y) > 0.5 * seg_len) \
                    and (math.hypot(p1t0_x, p1t0_y, p2t0_x, p2t0_y) > seg_len) \
                    and (math.hypot(p2t0_x, p2t0_y, p1t1_x, p1t1_y) < 0.5 * seg_len):
                        memCur.execute(f"UPDATE labels SET(bodypart) VALUES(?) WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [p2, frame_ind+1, p1, indv])
                        memCon.commit()
                elif p2t1Q and None not in p2t1Q:
                    p2t1_x, p2t1_y, p2t1_conf = p2t1Q
                    if (math.hypot(p2t0_x, p2t0_y, p2t1_x, p2t1_x) > 0.5 * seg_len) \
                    and (math.hypot(p1t0_x, p1t0_y, p2t0_x, p2t0_y) > seg_len) \
                    and (math.hypot(p1t0_x, p1t0_y, p2t1_x, p2t1_y) < 0.5 * seg_len):
                        memCur.execute(f"UPDATE labels SET(bodypart) VALUES(?) WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [p1, frame_ind+1, p2, indv])
                        memCon.commit()
        
        # Vote on forward direction (Set direction of movement as head)
        for frame_ind in range(min_frame+1,max_frame+1):
            flip_vote = 0
            for p_i in range(1,len(points)-1):
                p_a = points[p_i-1]
                p_b = points[p_i]
                p_c = points[p_i+1]

                paQ_t0 = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind-1, p_a, indv]).fetchone()
                pbQ_t0 = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind-1, p_b, indv]).fetchone()
                pbQ_t1 = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p_b, indv]).fetchone()
                pcQ_t0 = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind-1, p_c, indv]).fetchone()

                if (paQ_t0 and pbQ_t0 and pcQ_t0 and pbQ_t1) and (None not in paQ_t0 and None not in pbQ_t0 and None not in pcQ_t0 and None not in pbQ_t1):
                    pa_x, pa_y = paQ
                    pb_t0_x, pb_t0_y = pbQ
                    pb_t1_x, pb_t1_y = pbQ
                    pc_x, pc_y, = pcQ

                    va = np.array((pa_x-pb_t0_x,pa_y-pb_t0_y)) / np.linalg.norm((pa_x-pb_t0_x,pa_y-pb_t0_y))
                    vc =  np.array((pc_x-pb_t0_x,pc_x-pb_t0_y)) / np.linalg.norm((pa_x-pb_t0_x,pa_y-pb_t0_y))
                    vb = (pb_t1_x-pb_t0_x,pb_t1_y-pb_t0_y)

                    if np.dot(va, vb) > np.dot(vc, vb):
                        flip_vote += 1
                    else:
                        flip_vote -= 1
            if flip_vote > 2:
                print("\nFLIP VOTE!\n")
                for p_i in range(len(points)):
                    memCur.execute(f"UPDATE labels SET(bodypart) VALUES(?) WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [points[len(points)-1-p_i]+"_f", frame_ind, points[p_i], indv])
                for p_i in range(len(points)):
                    memCur.execute(f"UPDATE labels SET(bodypart) VALUES(?) WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [points[p_i], frame_ind, points[p_i]+"_f", indv])

        # Delete labels that create impossible body segments
        for frame_ind in range(min_frame,max_frame):
            for p_i in range(1,len(points)-1):
                p_a = points[p_i-1]
                p_b = points[p_i]
                p_c = points[p_i+1]

                paQ = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p_a, indv]).fetchone()
                pbQ = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p_b, indv]).fetchone()
                pcQ = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p_c, indv]).fetchone()

                if (paQ and pbQ and pcQ) and (None not in paQ and None not in pbQ and None not in pcQ):
                    pa_x, pa_y, = paQ
                    pb_x, pb_y, = pbQ
                    pc_x, pc_y, = pcQ
                    if math.hypot(pb_x, pb_y, pa_x, pa_y) + math.hypot(pb_x, pb_y, pc_x, pc_y) > 4 * seg_len or math.hypot(pb_x, pb_y, pa_x, pa_y) > 2.5 * seg_len:
                        memCur.execute(f"DELETE FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p_b, indv]) # Deleting points should cut apart bad tracklets
                        memCon.commit()
                
        # Delete label jumps to cut apart bad tracklets
        for frame_ind in range(min_frame,max_frame):
            for p in points:
                pt0Q = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind, p, indv]).fetchone()
                pt1Q = memCur.execute(f"SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind+1, p, indv]).fetchone()

                if not (pt0Q and pt1Q and None not in pt0Q and None not in pt1Q):
                    continue
                pt0_x, pt0_y, = pt0Q
                pt1_x, pt1_y, = pt1Q
                if (math.hypot(pt0_x, pt0_y, pt1_x, pt1_y) > 0.5 * seg_len): # Points cannot jump half a segment length per frame
                    memCur.execute(f"DELETE FROM labels WHERE frame_num = ? AND bodypart = ? AND indiv = ?", [frame_ind+1, p, indv]) # Deleting points should cut apart bad tracklets
                    memCon.commit()
        """

        #Calc speed
        video_path = os.path.abspath(f"../data/ingest/videos/{vidMD5}.mp4")
        src_video = cv2.VideoCapture(video_path)
        fps = src_video.get(cv2.CAP_PROP_FPS)
        step_size = int(fps*STEP_TIME)+1
        data = []
        print(f"Calculating possible tracklets of {indv} for {vidMD5}")
        tracklet = [0,-1,[]]
        for frame_ind in range(min_frame+step_size,max_frame+1,step_size):
            entry = []
            for bodypart in parts_list[1:-1]: # Ignore ends of the worms
                x_pos_prev = np.NaN
                y_pos_prev = np.NaN
                prev_q = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', (frame_ind-step_size, indv, bodypart) ).fetchone()
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
                if distance > seg_len*2:
                    distance = np.NaN
                entry.append(distance)
            if np.isnan(np.array(entry)).sum() > 2:
                tracklet[1] = frame_ind
                data.append(tracklet)
                tracklet = [frame_ind+1,-1,[]]
            else:
                pruned_entry = [x if abs(x - np.median(entry)) < 1.5 * np.std(entry) else np.NaN for x in entry ]
                tracklet[2].append(pruned_entry)
        tracklet[1] = range(min_frame+step_size,max_frame+1,step_size)[-1]
        data.append(tracklet)

        longest_tracklet = max(data, key=lambda x: x[1]-x[0])

        print(f"Calculating speed of {indv} for {vidMD5}")
        if len(longest_tracklet[2]) == 0:
            print(f"The longest tracklet of {indv} for {vidMD5} was empty.")
            raise ValueError
        speed = np.nanmean(np.array(longest_tracklet[2]))/step_size*fps
        print("Testing speed is a valid value.")
        if np.isnan(speed):
            print(f"The speed of {indv} for {vidMD5} was NaN.")
            raise ValueError
        elif len(longest_tracklet[2]) <  len(range(min_frame+step_size,max_frame+1,step_size))/4:
            print(f"The longest tracklet of {indv} for {vidMD5} did not meet length threshold")
            continue
        print("Assigning confidence value.")
        confidence = True
        if longest_tracklet[1] - longest_tracklet[0] < (max_frame-min_frame-step_size)/2:
            print(f"Length for longest tracklet of {indv} for {vidMD5} was too short for confidence. {longest_tracklet[1] - longest_tracklet[0]} < {(max_frame-min_frame-step_size)/3}")
            confidence = False
        speed_data.append( (indv,speed,confidence, longest_tracklet[0:2]) )
    
    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    intended_numIndv = cur.execute("SELECT numInd FROM videos WHERE vidMD5 = ?", [vidMD5]).fetchone()[0]
    con.close()
    if len(speed_data) == 0:
        print(f"No speed data was found for {vidMD5}.")
        raise ValueError
    elif len(speed_data) == intended_numIndv:
        mark_complete(vidMD5)
    elif len(speed_data) in range(intended_numIndv-1,intended_numIndv+2):
        mark_warning(vidMD5)
    else:
        mark_error(vidMD5)

    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    for v in speed_data:
        indv,speed,confidence,_ = v
        cur.execute("INSERT OR REPLACE INTO detectedIndv(vidMD5, ind, speed, confidence) VALUES(?,?,?,?)",
                    [vidMD5,indv,speed,confidence])
    con.commit()
    con.close()

    # Make labeled video
    label_ind_bounds = []
    for v in speed_data:
        indv,_,_,bounds = v
        label_ind_bounds.append([indv,bounds])
    
    out_video = cv2.VideoWriter(f'../data/outputs/{vidMD5}_labeled.mp4', 
                                cv2.VideoWriter_fourcc(*'mp4v'), 
                                fps / step_size, 
                                (int(src_video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(src_video.get(cv2.CAP_PROP_FRAME_HEIGHT))))
    frame_ind = 0
    for frame_ind in range(min_frame+step_size,max_frame+1,step_size):
        src_video.set(cv2.CAP_PROP_POS_FRAMES, frame_ind)
        ret, frame = src_video.read()
        for indv in [x[0] for x in filter(lambda x: frame_ind in range(x[1][0],x[1][1]),label_ind_bounds)]:
            x0,y0 = memCur.execute('SELECT MIN(x_pos), MIN(y_pos) FROM labels WHERE frame_num = ? AND indiv = ?', [frame_ind, indv]).fetchone()
            x1,y1 = memCur.execute('SELECT MAX(x_pos), MAX(y_pos) FROM labels WHERE frame_num = ? AND indiv = ?', [frame_ind, indv]).fetchone()
            if x0 is None or y0 is None or x1 is None or y1 is None:
                print("Box boundaries had NoneType", x0,y0,x1,y1)
                continue
            cv2.rectangle(frame, (int(x0-20),int(y0-20)), (int(x1+20),int(y1+20)), (115, 158, 0), 4)
            cv2.putText(frame, indv, (int(x0-20),int(y0-25)), cv2.FONT_HERSHEY_SIMPLEX, 2, (115, 158, 0), 4, cv2.LINE_AA)
            parts_list = ['head', '1/8_point', '1/4_point', '3/8_point', '1/2_point', '5/8_point', '3/4_point', '7/8_point', 'tail']
            for i in range(2,len(parts_list)-1):
                pointQ1 = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', [frame_ind, indv, parts_list[i-1]]).fetchone()
                pointQ2 = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', [frame_ind, indv, parts_list[i]]).fetchone()
                if pointQ1 is not None and pointQ2 is not None:
                    if x0 is None or y0 is None or x1 is None or y1 is None:
                        print("Body part segment had NoneType", x0,y0,x1,y1)
                        continue
                    x0,y0 = pointQ1
                    x1,y1 = pointQ2
                    cv2.line(frame, (int(x0),int(y0)), (int(x1),int(y1)), (115, 158, 0), 4)
            for part in parts_list[1:-1]:
                pointQ = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', [frame_ind, indv, part]).fetchone()
                if pointQ is not None:
                    x0,y0 = pointQ
                    if x0 is None or y0 is None:
                        print("Body part had NoneType", x0,y0)
                        continue
                    if part == '1/8_point':
                        cv2.circle(frame, (int(x0),int(y0)), 16, (0, 94, 213), -1)
                    else:
                        cv2.circle(frame, (int(x0),int(y0)), 16, (115, 158, 0), -1)
        out_video.write(frame)
    src_video.release()
    out_video.release()

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

def mark_error(vidMD5):
    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    cur.execute("UPDATE videos SET proc_state = 'error' WHERE vidMD5 = ?", [vidMD5])
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
        os.rename(f'../data/intermediates/{labeled_video}', f'../data/outputs/{vidMD5}_prelabeled.mp4')
    purgelist = [f'../data/intermediates/{entry}' for entry in os.listdir('../data/intermediates/') if entry.startswith(vidMD5)]
    for item in purgelist:
        os.remove(item)

while True:
    vidMD5, numInd = acquire_video_job()
    print(f'Found job: {vidMD5}')
    try:
        for attempt in range(4):
            try:
                if attempt == 0:
                    dlc_track_data_generation(vidMD5, numInd)
                elif attempt == 1:
                    if numInd - 1 < 1:
                        raise ValueError
                    dlc_track_data_generation(vidMD5, numInd-1)
                elif attempt == 2:
                    dlc_track_data_generation(vidMD5, numInd+1)
                elif attempt == 3:
                    dlc_track_data_generation(vidMD5, None)
                
                track_data_processing(vidMD5)
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

    
