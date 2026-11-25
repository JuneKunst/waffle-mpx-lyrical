"""Import pinned OpenMANIPULATOR-X demonstrations and Flickr8k image-caption pairs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import av
import numpy as np
import pyarrow.parquet as pq
from PIL import Image
from huggingface_hub import hf_hub_download, HfFileSystem
from actions import JOINTS, LOW, HIGH, NAMES, SCHEMA

ARM='Hadolking/openmanipulator-pickplace-dataset-1114ep'
ARM_REV='f840ca6171f19987d6e4248ecbb1219231a4287a'
WEB='jxie/flickr8k'
WEB_REV='56f58c967835f7c508d684f36bd7897cca9d7634'
SHARD='data/train-00000-of-00002-2f8f6bfa852eac4b.parquet'


def fetch(name):
    return Path(hf_hub_download(ARM,name,revision=ARM_REV,repo_type='dataset'))


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def import_arm(destination,ids,stride):
    info=json.loads(fetch('meta/info.json').read_text())
    tasks={t['task_index']:t['task'] for t in map(json.loads,fetch('meta/tasks.jsonl').read_text().splitlines())}
    names=['joint_1','joint_2','joint_3','joint_4','gripper_position']
    targets=[f'joint_{i}_target' for i in range(1,5)]+['gripper_target']
    assert info['robot_type']=='open_manipulator_x' and info['features']['observation.state']['names']==names
    assert info['features']['action']['names']==targets and len(JOINTS)==5
    for episode in ids:
        path=destination/f'omx-{episode:06d}'
        if path.exists():
            meta=json.loads((path/'episode.json').read_text())
            existing=[json.loads(line) for line in (path/'frames.jsonl').read_text().splitlines()]
            if (meta.get('revision')==ARM_REV and meta.get('stride')==stride and
                meta.get('source_episode')==episode and len(existing)==meta['frames'] and
                all((path/r['image']).is_file() for r in existing)):
                print('Reusing',path,flush=True)
                continue
            raise ValueError(f'Existing episode differs or is incomplete: {path}')
        fmt=dict(episode_index=episode,episode_chunk=episode//info['chunks_size'],video_key='observation.images.rgb')
        data=fetch(info['data_path'].format(**fmt))
        video=fetch(info['video_path'].format(**fmt))
        rows=pq.read_table(data).to_pylist()
        fps=info['fps']; saved=clipped=decoded=0
        with TemporaryDirectory(dir=destination) as tmp:
            stage=Path(tmp)/'episode';stage.mkdir()
            with av.open(str(video)) as container,(stage/'frames.jsonl').open('w') as output:
                for i,frame in enumerate(container.decode(video=0)):
                    if i>=len(rows): raise ValueError('Extra video frames')
                    row=rows[i]; decoded+=1
                    if row['frame_index']!=i or row['episode_index']!=episode:raise ValueError('Frame index mismatch')
                    if frame.pts is None or abs(float(frame.pts*frame.time_base)-row['timestamp'])>1/fps:
                        raise ValueError('Timestamp mismatch')
                    if i%stride: continue
                    # Position traces frequently copy state into action. Use an explicit
                    # future recorded target to learn where the operator moves next.
                    future=rows[min(i+stride,len(rows)-1)]
                    state=np.r_[0.,0.,row['observation.state']]
                    action=np.r_[0.,0.,future['action']]
                    if not np.isfinite(np.r_[state,action]).all():raise ValueError('Non-finite sample')
                    if np.any(action<LOW) or np.any(action>HIGH):clipped+=1
                    item=f'{saved:07d}.jpg'
                    frame.to_image().convert('RGB').save(stage/item,quality=90)
                    output.write(json.dumps(dict(time=row['timestamp'],image=item,state=state.tolist(),
                        action=np.clip(action,LOW,HIGH).tolist(),source_frame=i,target_frame=future['frame_index']))+'\n')
                    saved+=1
            if decoded!=len(rows) or not saved:raise ValueError('Incomplete video')
            if len(set(row['task_index'] for row in rows))!=1:raise ValueError('Multiple instructions in one episode')
            write_json(stage/'episode.json',dict(schema=SCHEMA,state=NAMES,action=NAMES,
                instruction=tasks[rows[0]['task_index']],repo=ARM,revision=ARM_REV,source_episode=episode,
                fps=fps,stride=stride,command_lookahead_s=stride/fps,base='stationary',
                joint_unit_assumption='joint_1..4 rad, gripper m; matched names and numerical ranges',
                frames=saved,frames_with_clipped_targets=clipped,parquet_sha256=checksum(data),video_sha256=checksum(video)))
            stage.rename(path)
        print(path,saved,'frames,',clipped,'commands clipped',flush=True)


def import_web(dest,count):
    path=dest/'web'
    if path.exists():
        meta=json.loads((path/'source.json').read_text())
        rows=[json.loads(l) for l in (path/'captions.jsonl').read_text().splitlines()]
        if meta.get('revision')==WEB_REV and meta['rows']==count==len(rows) and all((path/r['image']).is_file() for r in rows):
            print('Reusing',path,flush=True)
            return
        raise ValueError(f'Existing caption sample differs or is incomplete: {path}')
    fs=HfFileSystem()
    source=f'datasets/{WEB}@{WEB_REV}/{SHARD}'
    with TemporaryDirectory(dir=dest) as tmp:
        stage=Path(tmp)/'web';stage.mkdir()
        with fs.open(source,'rb',block_size=2**20) as remote:
            parquet=pq.ParquetFile(remote)
            saved=0
            with (stage/'captions.jsonl').open('w') as output:
                for batch in parquet.iter_batches(batch_size=min(count,16),columns=['image','caption_0']):
                    for row in batch.to_pylist():
                        item=f'{saved:05d}.jpg'
                        with Image.open(io.BytesIO(row['image']['bytes'])) as im: im.convert('RGB').save(stage/item)
                        output.write(json.dumps(dict(image=item,text=row['caption_0'],row=saved))+'\n')
                        saved+=1
                        if saved>=count: break
                    if saved>=count:break
        if saved!=count: raise ValueError('Insufficient captioned images')
        write_json(stage/'source.json',dict(repo=WEB,revision=WEB_REV,file=SHARD,rows=count))
        stage.rename(path)
    print(path,count,'web image-caption pairs',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('--episodes',nargs='+',type=int,default=[0,1,2,3])
    p.add_argument('--stride',type=int,default=6);p.add_argument('--captions',type=int,default=16)
    p.add_argument('--only',choices=['arm','web','both'],default='both')
    args=p.parse_args()
    if args.stride<1 or args.captions<2:p.error('Require positive stride and at least two captions')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.only in ('arm','both'):import_arm(args.output,args.episodes,args.stride)
    if args.only in ('web','both'):import_web(args.output,args.captions)
