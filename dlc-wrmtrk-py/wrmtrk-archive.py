#!/usr/bin/python3
from datetime import datetime
import shutil
import sqlite3, os

DB_PATH = '../data/server.db'
SQLITE3_TIMEOUT = 20

archive_id = datetime.now().strftime("%Y%m%d-%H%M%S")
os.mkdir(f'../data/archives/{archive_id}')
os.mkdir(f'../data/archives/{archive_id}/videos')
os.mkdir(f'../data/archives/{archive_id}/videos/raw')
os.mkdir(f'../data/archives/{archive_id}/videos/labeled')
os.mkdir(f'../data/archives/{archive_id}/normalizingImages')
arc_con = sqlite3.connect(f'../data/archives/{archive_id}/server.db')
arc_cur = arc_con.cursor()

arc_cur.execute("CREATE TABLE IF NOT EXISTS plates (plateUUID TEXT PRIMARY KEY, plateID TEXT, primaryLabel TEXT, secondaryLabel TEXT, normMD5 TEXT, uploadTime TEXT);")
arc_cur.execute("CREATE TABLE IF NOT EXISTS conditions (plateUUID TEXT, condTag TEXT, UNIQUE (plateUUID,condTag));")
arc_cur.execute("CREATE TABLE IF NOT EXISTS videos (plateUUID TEXT, vidMD5 TEXT UNIQUE, filename TEXT, proc_state TEXT, numInd INTEGER, uploadTime TEXT);")
arc_cur.execute("CREATE TABLE IF NOT EXISTS detectedIndv (vidMD5 TEXT, ind TEXT, speed REAL, confidence BOOLEAN, UNIQUE (vidMD5,ind));")
arc_cur.execute("CREATE TABLE IF NOT EXISTS normalization (normMD5 TEXT, value REAL, UNIQUE (normMD5,value));")

src_con = sqlite3.connect(DB_PATH, timeout=SQLITE3_TIMEOUT)
src_cur = src_con.cursor()

platesQ = src_cur.execute("SELECT plateUUID, plateID, primaryLabel, secondaryLabel, normMD5, uploadTime FROM plates").fetchall()

if platesQ is None:
    exit()

for plate_entry in platesQ:
    plateUUID, plateID, primaryLabel, secondaryLabel, normMD5, uploadTime = plate_entry

    arc_cur.execute("INSERT INTO plates(plateUUID, plateID, primaryLabel, secondaryLabel, normMD5, uploadTime) VALUES(?, ?, ?, ?, ?, ?)",
                    [plateUUID, plateID, primaryLabel, secondaryLabel, normMD5, uploadTime])
    arc_con.commit()
    src_cur.execute("DELETE FROM plates WHERE plateUUID = ?", [plateUUID])
    src_con.commit()

    conditionsQ = src_cur.execute("SELECT condTag FROM conditions WHERE plateUUID = ?", [plateUUID]).fetchall()
    for condTag_entry in conditionsQ:
        condTag = condTag_entry[0]
        arc_cur.execute("INSERT INTO conditions(plateUUID, condTag) VALUES(?, ?)", [plateUUID, condTag])
        src_cur.execute("DELETE FROM conditions WHERE plateUUID = ? AND condTag = ?", [plateUUID, condTag])
    arc_con.commit()
    src_con.commit()
    
    normVal = src_cur.execute("SELECT value FROM normalization WHERE normMD5 = ?", [normMD5]).fetchone()[0]
    arc_cur.execute("INSERT INTO normalization(normMD5, value) VALUES(?, ?)", [normMD5, normVal])
    arc_con.commit()
    src_cur.execute("DELETE FROM normalization WHERE normMD5 = ?", [normMD5])
    src_con.commit()
    shutil.copyfile(f'../data/ingest/normalizingImages/{normMD5}.png',f'../data/archives/{archive_id}/normalizingImages/{normMD5}.png')

    videosQ = src_cur.execute("SELECT vidMD5, filename, proc_state, numInd, uploadTime FROM videos WHERE plateUUID = ?", [plateUUID]).fetchall()

    if videosQ is None:
        continue
    for video_entry in videosQ:
        vidMD5, filename, proc_state, numInd, uploadTime = video_entry

        arc_cur.execute("INSERT INTO videos(plateUUID, vidMD5, filename, proc_state, numInd, uploadTime) VALUES(?, ?, ?, ?, ?, ?)",
                        [plateUUID, vidMD5, filename, proc_state, numInd, uploadTime])
        arc_con.commit()
        src_cur.execute("DELETE FROM videos WHERE vidMD5 = ?", [vidMD5])
        src_con.commit()

        shutil.move(f'../data/ingest/videos/{vidMD5}.mp4',f'../data/archives/{archive_id}/videos/raw/{vidMD5}.mp4')

        indvsQ = src_cur.execute("SELECT ind, speed, confidence FROM detectedIndv WHERE vidMD5 = ?", [vidMD5]).fetchall()
        if indvsQ is None:
            continue
        for indv_entry in indvsQ:
            ind, speed, confidence = indv_entry
            arc_cur.execute("INSERT INTO detectedIndv(vidMD5, ind, speed, confidence) VALUES(?, ?, ?, ?)",
                            [vidMD5, ind, speed, confidence])
            arc_con.commit()
            src_cur.execute("DELETE FROM detectedIndv WHERE vidMD5 = ? and ind = ?", [vidMD5, ind])
            src_con.commit()

normMD5_purgelist = set([normMD5 for (normMD5) in arc_cur.execute("SELECT normMD5 FROM plates").fetchall()]).difference(set([normMD5 for (normMD5) in src_cur.execute("SELECT normMD5 FROM plates").fetchall()]))

for entry in normMD5_purgelist:
    normMD5 = entry[0]
    os.remove(f'../data/ingest/normalizingImages/{normMD5}.png')