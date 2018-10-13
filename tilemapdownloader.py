from urllib import request
import bpy

from bpy.props import IntProperty, StringProperty

import numpy as np

import os
import tempfile
import re
import pprint


bl_info = {
    "name": "GSI Tile To Static Map",
    "author": "Toda Shuta",
    "version": (1, 0, 0),
    "blender": (2, 79, 0),
    "location": "Image Editor",
    "description": "GSI Tile To Static Map",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Image"
}


bpy.types.Scene.gsitiletostaticmap_zoomlevel    = IntProperty(name="ズームレベル", default=18)
bpy.types.Scene.gsitiletostaticmap_topleftX     = IntProperty(name="左上タイルX",  default=229732)
bpy.types.Scene.gsitiletostaticmap_topleftY     = IntProperty(name="左上タイルY",  default=104096)
bpy.types.Scene.gsitiletostaticmap_bottomrightX = IntProperty(name="右下タイルX",  default=229740)
bpy.types.Scene.gsitiletostaticmap_bottomrightY = IntProperty(name="右下タイルY",  default=104101)
bpy.types.Scene.gsitiletostaticmap_urlfmt       = StringProperty(name="URL形式",   default="https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg")


def main(report, urlfmt, zoomlevel, topleftX, topleftY, bottomrightX, bottomrightY):
    tiles = []

    #zoomlevel = 18
    #topleftX = 229732
    #topleftY = 104096
    #bottomrightX = 229740
    #bottomrightY = 104101

    '''
    zoomlevel = 17
    topleftX = 114895
    topleftY = 52023
    bottomrightX = 114906
    bottomrightY = 52034
    '''

    combined_x_px = (bottomrightX-topleftX+1)*256
    combined_y_px = (bottomrightY-topleftY+1)*256

    #urlfmt = "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png"
    #urlfmt = "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
    ext = os.path.splitext(urlfmt)[1]
    tmp = tempfile.TemporaryFile(suffix=ext, delete=False).name

    # タイル座標は、
    # - 東方向がX正方向
    # - 南方向がY正方向
    # なので、左上からダウンロードするのが順当であるが、
    # 結合処理の都合で、左下から順にダウンロードしている
    #
    # ダウンロード順のイメージ:
    # 11 12 13 14 15
    #  6  7  8  9 10
    #  1  2  3  4  5
    #
    # タイル座標のイメージ(X,Y):
    # (0,0) (1,0) (2,0)
    # (0,1) (1,1) (2,1)
    # (0,2) (1,2) (2,2)
    for y in reversed(range(topleftY, bottomrightY+1)):
        for x in range(topleftX, bottomrightX+1):
            #print(zoomlevel, x, y)
            url = urlfmt.replace("{z}", str(zoomlevel)).replace("{x}", str(x)).replace("{y}", str(y))
            request.urlretrieve(url, tmp)
            img = bpy.data.images.load(tmp)
            tiletype = re.search("([^/]+)/\d+/\d+/\d+\.\w+$", url).group(1)
            img.name = "{}-{}-{}-{}".format(tiletype,zoomlevel,x,y)
            img.use_fake_user = True
            img.pack()
            img.filepath = ""
            tiles.append(img)
            print(img.name)

    os.remove(tmp)

    #print(tiles)

    combined_img = bpy.data.images.new("Combined Image", combined_x_px, combined_y_px, alpha=True)
    combined_pxs = np.array(combined_img.pixels[:])
    combined_pxs.resize(combined_y_px, combined_x_px*4)

    combined_R = combined_pxs[::,0::4]
    combined_G = combined_pxs[::,1::4]
    combined_B = combined_pxs[::,2::4]
    combined_A = combined_pxs[::,3::4]

    tile_idx = 0
    for yy in range(0,combined_y_px,256):
        for xx in range(0,combined_x_px,256):

            print(tile_idx, yy, xx, tiles[tile_idx])

            tile = tiles[tile_idx]
            tile_pxs = np.array(tile.pixels[:])
            tile_pxs.resize(256, 256*4)

            tile_R = tile_pxs[::,0::4]
            tile_G = tile_pxs[::,1::4]
            tile_B = tile_pxs[::,2::4]
            tile_A = tile_pxs[::,3::4]
            tile_idx += 1

            for y in range(256):
                for x in range(256):
                    combined_R[y+yy][x+xx] = tile_R[y][x]
                    combined_G[y+yy][x+xx] = tile_G[y][x]
                    combined_B[y+yy][x+xx] = tile_B[y][x]
                    combined_A[y+yy][x+xx] = tile_A[y][x]

    combined_pxs = combined_pxs.flatten()
    combined_img.pixels = combined_pxs
    combined_img.use_fake_user = True
    combined_img.pack(as_png=True)

    report({"INFO"}, "UV/画像エディターで {} を見てください".format(pprint.pformat(combined_img.name)))


class GsiTileToStaticMap(bpy.types.Operator):
    bl_idname = "object.gsitiletostaticmap"
    bl_label = "GSI Tile To Static Map"

    @classmethod
    def poll(cls, context):
        scene = context.scene
        if not scene.gsitiletostaticmap_topleftX < scene.gsitiletostaticmap_bottomrightX:
            return False
        if not scene.gsitiletostaticmap_topleftY < scene.gsitiletostaticmap_bottomrightY:
            return False
        return True

    def execute(self, context):
        scene = context.scene
        main(self.report,
                scene.gsitiletostaticmap_urlfmt,
                scene.gsitiletostaticmap_zoomlevel,
                scene.gsitiletostaticmap_topleftX, scene.gsitiletostaticmap_topleftY,
                scene.gsitiletostaticmap_bottomrightX, scene.gsitiletostaticmap_bottomrightY)
        return {"FINISHED"}


class GsiTileToStaticMapCustomMenu(bpy.types.Panel):
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "TOOLS"
    bl_label = "GSI Tile To Static Map"
    bl_category = "GSI Tile"
    #bl_context = "mesh_edit"
    #bl_context = "objectmode"

    @classmethod
    def poll(cls, context):
        return True

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "gsitiletostaticmap_urlfmt")
        layout.separator()
        layout.prop(context.scene, "gsitiletostaticmap_zoomlevel")
        layout.separator()
        layout.prop(context.scene, "gsitiletostaticmap_topleftX")
        layout.prop(context.scene, "gsitiletostaticmap_topleftY")
        layout.separator()
        layout.prop(context.scene, "gsitiletostaticmap_bottomrightX")
        layout.prop(context.scene, "gsitiletostaticmap_bottomrightY")
        layout.separator()
        layout.operator(GsiTileToStaticMap.bl_idname, text="Generate Static Map Image")


def register():
    bpy.utils.register_module(__name__)


def unregister():
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
