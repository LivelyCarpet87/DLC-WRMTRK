#!/usr/bin/python3
import math
import sqlite3, os
import deeplabcut as dlc
import numpy as np
import cv2
import torch
from multiprocessing import Pool

torch.backends.nnpack.enabled = False

DB_PATH = '../data/server.db'
SQLITE3_TIMEOUT = 20
SHUFFLE=2
DLC_CFG_PATH = os.path.abspath("/home/biosci/Documents/DLC-WrmTrk-Tyllis Xu-2025-10-25/config.yaml")
STEP_TIME = 0.1
SKELETON= ['pharynx-tip', 'pharynx-end', '1/4-point', '3/8-point', 'midpoint', '5/8-point', '3/4-point', '7/8-point', 'tail-tip']
TRACK_METHOD = 'skeleton'

con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
cur = con.cursor()
cur.execute('UPDATE videos SET proc_state = "pending" WHERE proc_state = "processing"')
con.commit()
con.close()

purgelist = [f'../data/intermediates/{entry}' for entry in os.listdir('../data/intermediates/') if entry != '.gitignore']
for item in purgelist:
    os.remove(item)

def get_body_pos_never_null_query_generator():
    query = "SELECT \n"

    for label_i in range(len(SKELETON)):
        query += f"tb{label_i}.x_pos AS lb{label_i}_x, tb{label_i}.y_pos AS lb{label_i}_y,\n"
    
    query = query[:-2] + '\n'
    query += "FROM labels AS tb0 \n"

    for label_i in range(1,len(SKELETON)):
        query += f"JOIN labels AS tb{label_i} ON tb{label_i}.frame_num = tb0.frame_num AND tb{label_i}.indiv = tb0.indiv "
        query += f"AND tb{label_i}.bodypart = '{SKELETON[label_i]}' AND tb{label_i}.x_pos IS NOT NULL AND tb{label_i}.y_pos IS NOT NULL \n"
    
    query += "WHERE \n"
    query += f"tb0.bodypart = '{SKELETON[0]}' AND \n"
    query += "tb0.indiv = ? AND \n"
    query += "tb0.x_pos IS NOT NULL AND \n"
    query += "tb0.y_pos IS NOT NULL;"
    # print(query)
    return query

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
                            destfolder=os.path.abspath(f"../data/intermediates"), draw_skeleton=False, color_by='bodypart', track_method=TRACK_METHOD)
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

    indv_lens = {}
    speed_data = {}

    for indv in [f"ind{i}" for i in range(1,numInd+1)]:
        # Calc len
        print(f"Calculating length of {indv} for {vidMD5}")

        memCur.execute(get_body_pos_never_null_query_generator(), (indv,))
        rows = memCur.fetchall()
        print(f"Got {len(rows)} perfect frames...")

        lengths = []
        for row in rows:
            length = 0.0
            for i in range(len(SKELETON) - 1):
                x1, y1 = row[2 * i], row[2 * i + 1]
                x2, y2 = row[2 * (i + 1)], row[2 * (i + 1) + 1]
                length += math.hypot( x1 - x2, y1 - y2)
            if not np.isnan(length):
                lengths.append(length)
        if len(lengths) == 0:
            print(f"Unable to acquire median length for {indv} of {vidMD5}")
            continue
        indv_lens[indv] = np.median(lengths)
        speed_data[indv] = []

    """
        #Calc speed
        data = []
        for frame_ind in range(min_frame+step_size,max_frame+1):
            entry = []
            

        weighted_avg_distance = 0
        sum_weights = 0
        for d, p in data:
            if not np.isnan(d) and p > 0:
                weighted_avg_distance += d*p
                sum_weights += p
        
        print(f"Calculating speed of {indv} for {vidMD5}")
        if sum_weights == 0:
            print(f"The longest tracklet of {indv} for {vidMD5} was empty.")
            raise ValueError
        speed = (weighted_avg_distance/sum_weights) /step_size*fps
        print("Testing speed is a valid value.")
        if np.isnan(speed):
            print(f"The speed of {indv} for {vidMD5} was NaN.")
            raise ValueError
        print("Assigning confidence value.")
        confidence = True
        if sum_weights/ len(data)< 0.7:
            confidence=False
        speed_data.append( (indv,speed,confidence) )
    
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
    """

    # Find FPS and Step Size
    video_path = os.path.abspath(f"../data/ingest/videos/{vidMD5}.mp4")
    src_video = cv2.VideoCapture(video_path)
    fps = src_video.get(cv2.CAP_PROP_FPS)
    step_size = int(fps*STEP_TIME)+1

    # Make labeled video
    out_video = cv2.VideoWriter(f'../data/outputs/{vidMD5}_labeled.mp4', 
                                cv2.VideoWriter_fourcc(*'mp4v'), 
                                fps / step_size, 
                                (int(src_video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(src_video.get(cv2.CAP_PROP_FRAME_HEIGHT))))
    
    for frame_ind in range(min_frame+step_size,max_frame+1, 1):
        src_video.set(cv2.CAP_PROP_POS_FRAMES, frame_ind)
        ret, frame = src_video.read()
        for indv in [f"ind{i}" for i in range(1,numInd+1)]:
            x0,y0 = memCur.execute('SELECT MIN(x_pos), MIN(y_pos) FROM labels WHERE frame_num = ? AND indiv = ?', [frame_ind, indv]).fetchone()
            x1,y1 = memCur.execute('SELECT MAX(x_pos), MAX(y_pos) FROM labels WHERE frame_num = ? AND indiv = ?', [frame_ind, indv]).fetchone()
            if x0 is None or y0 is None or x1 is None or y1 is None:
                print("Box boundaries had NoneType", x0,y0,x1,y1)
                continue
            cv2.rectangle(frame, (int(x0-20),int(y0-20)), (int(x1+20),int(y1+20)), (115, 158, 0), 4)
            cv2.putText(frame, indv, (int(x0-20),int(y0-25)), cv2.FONT_HERSHEY_SIMPLEX, 2, (115, 158, 0), 4, cv2.LINE_AA)

            seg_len = indv_lens[indv] / (len(SKELETON)-1)

            for bodypart_index in range(1, len(SKELETON)-1): # Ignore ends of the worms
                bodypart =  SKELETON[bodypart_index]
                bodypart_pred =  SKELETON[bodypart_index-1]
                confidence = 0

                x_pos_prev = np.NaN
                y_pos_prev = np.NaN
                prev_q = memCur.execute('SELECT x_pos, y_pos, confidence FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', (frame_ind-step_size, indv, bodypart) ).fetchone()
                if prev_q is not None:
                    x_pos_prev = prev_q[0]
                    y_pos_prev = prev_q[1]
                    confidence += prev_q[2] / 2

                x_pos_now = np.NaN
                y_pos_now = np.NaN
                now_q = memCur.execute('SELECT x_pos, y_pos, confidence FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', (frame_ind, indv, bodypart) ).fetchone()
                if now_q is not None:
                    x_pos_now = now_q[0]
                    y_pos_now = now_q[1]
                    confidence += now_q[2] / 2
                
                x_pos_pred_prev = np.NaN
                y_pos_pred_prev = np.NaN
                pred_q = memCur.execute('SELECT x_pos, y_pos FROM labels WHERE frame_num = ? AND indiv = ? AND bodypart = ?', (frame_ind-step_size, indv, bodypart_pred) ).fetchone()
                if now_q is not None:
                    x_pos_pred_prev = pred_q[0]
                    y_pos_pred_prev = pred_q[1]

                if None in [x_pos_prev, y_pos_prev, x_pos_now, y_pos_now, x_pos_pred_prev, y_pos_pred_prev]:
                    distance = np.NaN
                    confidence = 0

                shadow_parts_q = memCur.execute('SELECT indiv FROM labels WHERE frame_num = ? AND indiv < ? AND bodypart = ? '+
                                                        'AND x_pos between ? and ? AND y_pos between ? and ?', 
                                                        (frame_ind-step_size, indv, bodypart, 
                                                        x_pos_now-0.5*seg_len,x_pos_now+0.5*seg_len, y_pos_now-0.5*seg_len,y_pos_now+0.5*seg_len  ) 
                                                        ).fetchall()
                if len(shadow_parts_q) > 0: 
                    distance = np.NaN
                    confidence = 0
                    
                pos_prev = np.array( [x_pos_prev, y_pos_prev] )
                pos_now = np.array( [x_pos_now, y_pos_now] )
                pos_pred_prev = np.array( [x_pos_pred_prev, y_pos_pred_prev] )
                
                distance = np.linalg.norm(pos_now-pos_prev)

                if np.dot( (pos_now-pos_prev), (pos_pred_prev-pos_now) ) < 0:
                    distance *= -1
                
                if distance > seg_len*2:
                    distance = np.NaN
                    confidence = 0
                
                speed_data[indv].append([distance, confidence])
                if confidence > 0:
                    if bodypart == SKELETON[1]:
                        cv2.circle(frame, (int(x_pos_now),int(y_pos_now)), 16, (0, 94, 213), -1)
                    else:
                        cv2.circle(frame, (int(x_pos_now),int(y_pos_now)), 16, (115, 158, 0), -1)
                    cv2.line(frame, (int(x_pos_now),int(y_pos_now)), (int(x_pos_prev),int(y_pos_prev)), (115, 158, 0), 4)
                elif None not in [x_pos_now, y_pos_now]:
                    cv2.circle(frame, (int(x_pos_now),int(y_pos_now)), 16, (0,255,255), -1)
                    if None not in [x_pos_prev, y_pos_prev]:
                        cv2.line(frame, (int(x_pos_now),int(y_pos_now)), (int(x_pos_prev),int(y_pos_prev)), (0,255,255), 4)
        out_video.write(frame)
    src_video.release()
    out_video.release()


    for indv in [f"ind{i}" for i in range(1,numInd+1)]:
        print(f"Calculating speed of {indv} for {vidMD5}")
        weighted_avg_distance = 0
        sum_weights = 0
        for d, p in speed_data[indv]:
            if not np.isnan(d) and p > 0:
                weighted_avg_distance += d*p
                sum_weights += p
        print(f"Calculating speed of {indv} for {vidMD5}")
        if sum_weights == 0:
            print(f"The longest tracklet of {indv} for {vidMD5} was empty.")
            raise ValueError
        speed = (weighted_avg_distance/sum_weights) /step_size*fps
        print("Testing speed is a valid value.")
        if np.isnan(speed):
            print(f"The speed of {indv} for {vidMD5} was NaN.")
            raise ValueError
        print("Assigning confidence value.")

        confidence = True
        if sum_weights/ len(data)< 0.7:
            confidence=False
        
        speed_res.append( (indv,speed,confidence) )
        speed_res.append( (indv,speed,confidence) )
    
    con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
    cur = con.cursor()
    intended_numIndv = cur.execute("SELECT numInd FROM videos WHERE vidMD5 = ?", [vidMD5]).fetchone()[0]
    con.close()
    if len(speed_res) == 0:
        print(f"No speed data was found for {vidMD5}.")
        raise ValueError
    elif len(speed_res) == intended_numIndv:
        speed_res(vidMD5)
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

def core_loop(_):
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
                except ValueError as e:
                    print(f"detector failed, {e}")
                    cleanup(vidMD5)
                    if attempt == 2:
                        mark_failed(vidMD5)
                        raise ValueError
                except OSError as e:
                    mark_failed(vidMD5)
                    print(f"detector failed, {e}")
                    cleanup(vidMD5)
                    if attempt == 2:
                        mark_failed(vidMD5)
                        raise ValueError
        except ValueError:
            mark_failed(vidMD5)
        cleanup(vidMD5)

        
if __name__ == '__main__':
    with Pool(4) as mp:
        mp.map(core_loop, range(4))
