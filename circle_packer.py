import numpy as np
import argparse
from yaml import load
from art_utils.cairo_painter import CairoPainter
from art_utils.gradient import build_gradient, color_from_hex
from art_utils.interp import interpgrid
import time

class Circle:
    def __init__(self, cx, cy, r, color=None, separation=0):
        self.cx, self.cy, self.r = cx, cy, r
        self.color = color
    
    def overlap_with(self, cx, cy, r):
        # Determine distance between centers
        d = np.hypot(cx-self.cx,cy-self.cy)
        # Return true if that distance is greater than the sum of their radii
        return d < r + self.r + separation

def overlaps_with_mask(cx, cy, r, mask):
    o = np.cos(np.pi/4) * r
    pts = [[cx, cy],
        [cx - r, cy],
        [cx, cy + r],
        [cx + r, cy],
        [cx, cy - r],
        [cx + o, cy + o],
        [cx + o, cy - o],
        [cx - o, cy + o],
        [cx - o, cy - o]]
    if any([not mask.pixel_filled(pt[0],pt[1]) for pt in pts]):
        return False
    return True

class Circles:
    def __init__(self, path='./out.png', width=700, height=900, n=800, rmin=2, rmax=22, colors=None, lines=[], separation=0, line_width=0, mode='image', bgcolor=None):
        self.width, self.height = width, height
        self.n = n
        self.cx, self.cy = self.width / 2, self.height / 2
        self.rmin, self.rmax = rmin, rmax
        self.colors = colors or ['#77878B','#305252','#373E40','#488286']

        self.separation = separation
        self.line_width = line_width
        self.colors = [color_from_hex(color) for color in self.colors]

        self.maskpainter = CairoPainter(width=self.width, height=self.height)
        self.textbounds = [[self.width/2,self.height/2],[self.width/2,self.height/2]]
        if bgcolor is not None:
            bgcolor = color_from_hex(bgcolor)
        
        for line in lines:
            text = line.get('text', '')
            size = line.get('size', 36)
            x_off = line.get('x_offset', 0)
            y_off = line.get('y_offset', 0)
            font = line.get('font', 'Inter Black')
            color = color_from_hex(line.get('color', '000000'))
            bounds = self.maskpainter.draw_text(text, self.width/2+x_off,self.height/2+y_off, size=size, font=font, color=color_from_hex('ffffff'))
            self.textbounds[0][0] = min(self.textbounds[0][0],bounds[0][0]) # xmin
            self.textbounds[1][0] = max(self.textbounds[1][0],bounds[1][0]) # xmax
            self.textbounds[0][1] = min(self.textbounds[0][1],bounds[0][1]) # ymin
            self.textbounds[1][1] = max(self.textbounds[1][1],bounds[1][1]) # ymax

        xmin, xmax = self.textbounds[0][0], self.textbounds[1][0]
        ymin, ymax = self.textbounds[0][1], self.textbounds[1][1]
        print('Text width {} height {}'.format(xmax-xmin,ymax-ymin))
        if xmin < 0 or xmax >= self.width:
            print('Warning! Text is too wide')
        
        if ymin < 0 or ymax >= self.height:
            print('Warning! Text is too tall')

        self.maskpainter.output_snapshot('./mask.png')
        self.painter = CairoPainter(path=path, mode=mode, width=self.width, height=self.height, bg=bgcolor)

    
    def place_circle(self, r):
        # Guard number
        guard = 1000
        while guard:
            xmin, xmax = self.textbounds[0][0], self.textbounds[1][0]
            ymin, ymax = self.textbounds[0][1], self.textbounds[1][1]

            cx = xmin + (xmax-xmin)*np.random.random()
            cy = ymin + (ymax-ymin)*np.random.random()

            # Verify circle fits inside the larger circle
            if overlaps_with_mask(cx,cy,r,self.maskpainter):
                # Check for collisions with other circles
                if not any(circle.overlap_with(cx, cy, r) for circle in self.circles):
                    circle = Circle(cx, cy, r, color=np.random.randint(len(self.colors)),separation=self.separation)
                    self.circles.append(circle)
                    return
            guard -= 1
            
    def make_circles(self):
        self.circles = []
        r = self.rmin + (self.rmax - self.rmin) * np.random.random(self.n)
        r[::-1].sort()

        for i in range(self.n):
            self.place_circle(r[i])
        
    
    def draw(self):
        for circle in self.circles:
            if self.line_width != 0:
                self.painter.draw_hollow_circle([circle.cx, circle.cy], r=circle.r, color=self.colors[circle.color], width=self.line_width)
            else:
                self.painter.draw_circle([circle.cx, circle.cy], r=circle.r, color=self.colors[circle.color])
        self.painter.output_snapshot()

if __name__ == '__main__':
    # Load the configuration file
    parser = argparse.ArgumentParser(description='Generate a circle-packed image')
    parser.add_argument('config', type=argparse.FileType('r'))
    args = parser.parse_args()
    data = load(args.config) or dict()

    # Sanitize the configuration, insert defaults as needed
    colorlist = data.get('colors', ["fe7f2d","fcca46","a1c181","619b8a","233d4d"])
    n_circles = data.get('n_circles', 2000)
    rmin = data.get('r_min', 2)
    rmax = data.get('r_max', 22)
    image = data.get('image', {})
    width = image.get('width', 1080)
    height = image.get('height', 1080)
    bgcolor = image.get('bg', None)
    separation = data.get('separation', 0)
    line_width = data.get('line_width', 0)
    path = data.get('path', './out.png')
    mode = data.get('mode', 'image')
    print('Image size {}x{}, bg {}'.format(width,height,bgcolor))

    lines = data.get('lines', [])
    if len(lines) == 0:
        raise Exception('Lines were not specified')
    for line in lines:
        print(line)

    t = time.time()
    circles = Circles(path=path, n=n_circles, colors=colorlist, width=width, height=height, rmin=rmin, rmax=rmax, lines=lines, separation=separation, line_width=line_width, bgcolor=bgcolor, mode=mode)
    print('Finished preparation in {} seconds'.format(time.time()-t))

    t = time.time()
    circles.make_circles()
    print('Finished circle packing in {} seconds'.format(time.time()-t))

    t = time.time()
    circles.draw()
    print('Finished rendering in {} seconds'.format(time.time()-t))