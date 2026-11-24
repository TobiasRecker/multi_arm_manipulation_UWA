"""Compose native Gazebo camera pixels and encode 15 source fps at 2x / 30 fps."""
import argparse
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('/output'))
    p.add_argument('--preview', action='store_true')
    a = p.parse_args()
    d = json.loads((a.output / 'movie.json').read_text())
    out = a.output
    navy, white, muted = (29, 23, 16), (246, 244, 239), (181, 169, 150)
    yellow, red = (32, 222, 255), (65, 64, 255)

    def text(image, value, xy, size=1., color=white, thickness=1):
        cv2.putText(image, value, xy, cv2.FONT_HERSHEY_SIMPLEX, size, color, thickness, cv2.LINE_AA)

    def compose(left, right, f, index):
        canvas = np.full((1080, 1920, 3), navy, dtype=np.uint8)
        canvas[126:990, 24:1224] = left
        canvas[126:990, 1256:1896] = right
        text(canvas, 'UWA', (24, 48), 1.1, yellow, 2)
        text(canvas, 'COOPERATIVE MANIPULATION', (125, 48), .95, white, 2)
        text(canvas, 'Two arms hold. One arm works.', (26, 83), .65, muted)
        text(canvas, 'GAZEBO / OGRE2', (1575, 40), .62, muted)
        text(canvas, 'SIMULATION   |   2x   |   30 fps', (1510, 76), .59, white)
        text(canvas, 'CELL VIEW', (26, 115), .5, muted)
        text(canvas, 'WORKPIECE DETAIL', (1258, 115), .5, muted)
        # Opaque, high contrast phase caption within the cell viewport.
        cv2.rectangle(canvas, (42, 914), (1206, 974), navy, -1)
        cv2.rectangle(canvas, (42, 914), (48, 974), red if f['mode'] == 'DRILL' else yellow, -1)
        text(canvas, f['title'], (66, 954), .85, white, 2)
        cv2.circle(canvas, (1280, 1023), 6, yellow, -1)
        text(canvas, 'Drawing', (1298, 1030), .58, white)
        cv2.circle(canvas, (1457, 1023), 6, red, -1)
        text(canvas, 'Virtual drilling', (1475, 1030), .58, white)
        text(canvas, 'Motion-reference replay  /  traces illustrate tool paths', (26, 1031), .57, muted)
        cv2.rectangle(canvas, (24, 1055), (1896, 1061), (70, 59, 44), -1)
        progress = index / max(1, len(d['frames']) - 1)
        cv2.rectangle(canvas, (24, 1055), (24 + round(1872 * progress), 1061), yellow, -1)
        return canvas

    if a.preview:
        previews = out / 'preview'
        for path in sorted(previews.glob('*-overview.ppm')):
            index = int(path.name.split('-')[0])
            canvas = compose(cv2.imread(str(path)), cv2.imread(str(previews / f'{index}-detail.ppm')), d['frames'][index], index)
            cv2.imwrite(str(previews / (str(index) + '.jpg')), canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return
    target = out / 'uwa-carton-gazebo-2x.mp4'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y', '-f', 'rawvideo',
               '-pix_fmt', 'bgr24', '-s', '1920x1080', '-r', str(d['fps'] * 2), '-i', '-',
               '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-threads', '6',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        with (out / 'overview.rgb').open('rb') as left, (out / 'detail.rgb').open('rb') as right:
            for index, f in enumerate(d['frames']):
                l = np.frombuffer(left.read(1200 * 864 * 3), np.uint8).reshape(864, 1200, 3)[:, :, ::-1]
                r = np.frombuffer(right.read(640 * 864 * 3), np.uint8).reshape(864, 640, 3)[:, :, ::-1]
                frame = compose(l, r, f, index)
                encoder.stdin.write(frame.tobytes())
                if index % 300 == 0:
                    cv2.imwrite(str(out / f'frame-{index:05d}.jpg'), frame)
                    print(f'Encoded {index}/{len(d["frames"])}', flush=True)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError('Video encoding failed')
    probe = subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(target)], text=True)
    (out / 'ffprobe.json').write_text(probe)
    info = json.loads(probe)
    stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
    if (stream['width'], stream['height'], stream['r_frame_rate'], int(stream['nb_frames'])) != (1920, 1080, '30/1', len(d['frames'])):
        raise ValueError('Unexpected video frame count, size or rate')
    summary = {'file': target.name, 'width': 1920, 'height': 1080, 'source_fps': d['fps'],
               'video_fps': 30, 'speed': 2, 'frames': len(d['frames']),
               'duration_s': float(info['format']['duration']),
               'drawing_trace_segments': sum(not t['red'] for t in d['traces']),
               'drill_markers': sum(t['red'] for t in d['traces']),
               'archived_motion_phases': d['archived_motion_phases'],
               'chapters': d['chapters'], 'new_contact_physics': False}
    (out / 'video.json').write_text(json.dumps(summary, indent=2) + '\n')
    # The reproducible pose/asset package is retained; raw camera buffers are expendable.
    for name in ('overview.rgb', 'detail.rgb'):
        (out / name).unlink()
    print(json.dumps({k: v for k, v in summary.items() if k != 'chapters'}), flush=True)


if __name__ == '__main__':
    main()
