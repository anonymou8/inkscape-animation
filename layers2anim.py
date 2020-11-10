import inkex
from inkex.base import TempDirMixin
from inkex.command import take_snapshot as inkscape_snapshot, write_svg
import os, subprocess as sp, shutil

class AnimLayers(TempDirMixin, inkex.OutputExtension):
    def add_arguments(self, pars):
        pars.add_argument('--resolution', type=int, default=96)
        pars.add_argument('--fps', type=int, default=12)
        pars.add_argument('--loops', type=int, default=1)
        pars.add_argument('--crf', type=int, default=22)
        pars.add_argument('--rgb', type=inkex.Boolean, default=True)
        pars.add_argument('--rsvg', type=inkex.Boolean, default=True)
        pars.add_argument('--pngs', type=inkex.Boolean, default=False)
        pars.add_argument('--path', type=str, default='')
        pars.add_argument('--pngn', type=int, default=0)
        pars.add_argument('--ffplay', type=inkex.Boolean, default=False)

    def save(self, stream):
        layers = self.svg.xpath("//svg:g[@inkscape:groupmode='layer']")

        if len(layers) < 1:
            inkex.errormsg("No layers found.")
            return

        def show_layer(layer, show=True):
            if show:
                layer.style.update('display:inherit;opacity:1;')
            else:
                layer.style.update('display:none;')

        def show_parent_layers(layer, show=True):
            parent = layer
            while True:
                parent = parent.getparent()
                if parent.get('inkscape:groupmode') == 'layer':
                    show_layer(parent, show=show)
                else:
                    break
                    
        def rsvg_snapshot(document, dirname, name, dpi):
            path = os.path.join(dirname, name)
            width = round(self.svg.width * dpi / 96)
            write_svg(document, path+'.svg')
            args = f'rsvg-convert -w {width} -a -o {path}.png {path}.svg'
            sp.run(args.split())

        if self.options.rsvg:
            snapshot = rsvg_snapshot
        else:
            snapshot = inkscape_snapshot
        
        # first, hide everything
        for layer in layers:
            show_layer(layer, show=False)
        
        # if first layer is named 'bg' then show it forever
        if layers[0].get('inkscape:label') == 'bg':
            show_layer(layers[0])
            layers = layers[1:]
        
        i = 0
        for layer in layers:
            # do not generate an image for layers that have sublayers
            children = layer.getchildren()
            if children and children[0].get('inkscape:groupmode') == 'layer':
                continue
            
            show_parent_layers(layer)
            show_layer(layer)
            snapshot(self.document, dirname=self.tempdir, name=f'{i:04}', dpi=self.options.resolution)
            show_layer(layer, show=False)
            show_parent_layers(layer, show=False)
            
            # copy PNG file if the option enabled
            if self.options.pngs and self.options.path:
                f = os.path.join(self.tempdir, f'{i:04}.png')
                t = os.path.join(self.options.path, f'{i+self.options.pngn:04}.png')
                shutil.copyfile(f, t)
                
            i += 1
        
        # convert to mp4
        fps = self.options.fps
        crf = self.options.crf
        codec = ['libx264', 'libx264rgb'][self.options.rgb]
        pngs = os.path.join(self.tempdir, '%04d.png')
        mp4 = os.path.join(self.tempdir, 'temp.mp4')
        info = '-hide_banner -loglevel warning'
        loops = f'-vf loop={self.options.loops-1}:{i}'
        args = f'ffmpeg {info} -r {fps} -i {pngs} {loops} -c:v {codec} -crf {crf} {mp4}'
        sp.run(args.split())
        
        # save output
        with open(mp4, 'rb') as tmp4:
            shutil.copyfileobj(tmp4, stream)

        if self.options.pngs and not self.options.path:
            inkex.errormsg("PNG frames were not saved. Please, choose a path.")
            
        if self.options.ffplay:
            sp.run(f'ffplay -loglevel quiet -loop 0 {mp4}'.split())
        
if __name__ == '__main__':
    AnimLayers().run()
