"""Original geometric OFFAIR wordmark matching approved A direction.

Creates editable SVG and a 6400px transparent UI texture from the same contours.
Requires Pillow only when regenerating the source PNG; Unreal imports the PNG.
No screenshot pixels or third-party font files are used.
"""
from pathlib import Path
from PIL import Image, ImageDraw

# SVG coordinates, 1600 x 300. Separate contours use even-odd fill for counters.
GLYPHS = [
    (0, [
        'M 80 0 L 220 0 Q 300 0 300 80 L 300 220 Q 300 300 220 300 L 80 300 Q 0 300 0 220 L 0 80 Q 0 0 80 0 Z',
        'M 106 78 L 194 78 Q 216 78 216 100 L 216 200 Q 216 222 194 222 L 106 222 Q 84 222 84 200 L 84 100 Q 84 78 106 78 Z']),
    (344, ['M 0 0 L 216 0 L 216 76 L 80 76 L 80 116 L 194 116 L 194 190 L 80 190 L 80 300 L 0 300 Z']),
    (604, ['M 0 0 L 216 0 L 216 76 L 80 76 L 80 116 L 194 116 L 194 190 L 80 190 L 80 300 L 0 300 Z']),
    (864, [
        'M 112 0 L 206 0 L 314 300 L 218 300 L 195 238 L 105 238 L 82 300 L 0 300 Z',
        'M 150 80 L 119 168 L 179 168 Z']),
    (1222, ['M 0 0 L 80 0 L 80 300 L 0 300 Z']),
    (1346, [
        'M 0 0 L 159 0 Q 238 0 238 82 L 238 102 Q 238 157 184 176 L 254 300 L 159 300 L 98 190 L 80 190 L 80 300 L 0 300 Z',
        'M 80 68 L 144 68 Q 160 68 160 91 L 160 103 Q 160 126 144 126 L 80 126 Z']),
]


def points(path):
    tokens=iter(path.split()); result=[]; x=y=0
    for command in tokens:
        if command in ('M','L'):
            x,y=float(next(tokens)),float(next(tokens));result.append((x,y))
        elif command=='Q':
            cx,cy,ex,ey=(float(next(tokens)) for _ in range(4))
            for step in range(1,65):
                t=step/64;result.append(((1-t)**2*x+2*(1-t)*t*cx+t*t*ex,(1-t)**2*y+2*(1-t)*t*cy+t*t*ey))
            x,y=ex,ey
        elif command!='Z':raise ValueError(command)
    return result


def build():
    root=Path(__file__).resolve().parent
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="300" viewBox="0 0 1600 300">',
         '<title>OFFAIR — approved A wordmark</title>']
    factor=8
    mask=Image.new('L',(1600*factor,300*factor),0);draw=ImageDraw.Draw(mask)
    for offset,contours in GLYPHS:
        svg.append(f'<path transform="translate({offset} 0)" fill="white" fill-rule="evenodd" d="'+ ' '.join(contours)+'"/>')
        for index,contour in enumerate(contours):
            draw.polygon([((x+offset)*factor,y*factor) for x,y in points(contour)],fill=255 if index==0 else 0)
    svg.append('</svg>')
    (root/'offair-title-a.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8')
    # White RGB even in transparent texels prevents dark fringes under filtering.
    output=Image.new('RGBA',(6400,1200),(255,255,255,0))
    output.putalpha(mask.resize(output.size,Image.Resampling.LANCZOS))
    output.save(root/'offair-title-a.png',optimize=True)


if __name__=='__main__':build()
