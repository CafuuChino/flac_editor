from io import BytesIO
from PIL import Image
import math,json


HeadType = {'0': 'STREAMINFO',
            '1': 'PADDING',
            '2': 'APPLICATION',
            '3': ' SEEKTABLE',
            '4': 'VORBIS_COMMEN',
            '5': 'CUESHEET',
            '6': 'PICTURE', }
PictureType = {'0' :'Other',
               '1': '32x32 pixels \'file icon\' (PNG only)',
               '2': "Other file icon",
               '3' :'Cover (front)',
               '4' :'Cover (back)',
               '5' :'Leaflet page',
               '6' :'Media (e.g. label side of CD)',
               '7' :'Lead artist/lead performer/soloist',
               '8' :'Artist/performer',
               '9' :'Conductor',
               '10' :' Band/Orchestra',
               '11' :'Composer',
               '12' :'Lyricist/text writer',
               '13' :'Recording Location',
               '14' :'During recording',
               '15' :'During performance',
               '16' :'Movie/video screen capture',
               '17' :'A bright coloured fish',
               '18' :'Illustration',
               '19' :'Band/artist logotype',
               '20' :'Publisher/Studio logotype'}

MIME = {'PNG':'image/png',
                'JPEG':'image/jpeg',
                'JPG':'image/jpeg',
                'JPE':'image/jpeg',
                'TIF':'image/tiff',
                'TIFF':'image/tiff',
                'BMP':'image/bmp',
                'GIF':'image/gif'}

def hex2str(string, code='utf8', byteorder='big'):
    return int(string, 16).to_bytes(int(len(string)/2), byteorder).decode(code)

def get_image_info(image, image_type, description):
    image_type = image_type.to_bytes(length = 4, byteorder = 'big')
    height = image.size[0].to_bytes(length = 4, byteorder = 'big')
    width = image.size[1].to_bytes(length = 4, byteorder = 'big')
    if image.mode in ['RGB']:
        color_bit = int(24).to_bytes(length = 4, byteorder = 'big')
    elif image.mode in ['RGBA','CMYK']:
        color_bit = int(32).to_bytes(length = 4, byteorder = 'big')
    else:
        color_bit = int(24).to_bytes(length = 4, byteorder = 'big')
    thumbnail_bit = int(0).to_bytes(length = 4, byteorder = 'big')
    mime_type = bytes(MIME[image.format], encoding = 'ascii')
    mime_len = len(mime_type).to_bytes(length = 4, byteorder = 'big')
    description_bytes = bytes(description,encoding = 'utf-8')
    description_len = len(description_bytes).to_bytes(length = 4, byteorder = 'big')
    image_buf = BytesIO()
    image.save(image_buf,format = image.format)
    image_data = image_buf.getvalue()
    image_data_len = len(image_data).to_bytes(length = 4, byteorder = 'big')
    return image_type + mime_len + mime_type + description_len + description_bytes + width + height + color_bit + thumbnail_bit + image_data_len + image_data


class Flac(object):
    class MetaBlock(object):
        class MetaHeader(object):
            flag_mask = [0b10000000, 7]
            type_mask = [0b01111111, 0]
            def __init__(self, raw_bytes):
                self.raw = raw_bytes
                self.meta_flag = (self.raw[0] & self.flag_mask[0]) >> self.flag_mask[1]
                self.meta_type = (self.raw[0] & self.type_mask[0]) >> self.type_mask[1]
                self.meta_len  =  int().from_bytes(self.raw[1:4], byteorder='big', signed=True)

            def print(self):
                print('Meta flag :', self.meta_flag)
                print('Meta Type :', HeadType[str(self.meta_type)])
                print('Meta Len :', self.meta_len)

        def __init__(self, raw_bytes):
            self.raw = raw_bytes
            self.head = self.MetaHeader(self.raw[0:4])
            self.content = self.raw[4:]

    class StreamInfo(object):
        sampling_freq_mask = [0b1111111111111111111100000000000000000000000000000000000000000000,44]
        channel_mask = [0b0000000000000000000011100000000000000000000000000000000000000000,41]
        sampling_bit_mask = [0b0000000000000000000000011111000000000000000000000000000000000000,36]
        sampling_channel_mask = [0b0000000000000000000000000000111111111111111111111111111111111111,0]
        def __init__(self, raw_bytes):
            self.raw = raw_bytes
            self.min_block_size = int().from_bytes(self.raw[0:2], byteorder='big', signed=True)
            self.max_block_size = int().from_bytes(self.raw[2:4], byteorder='big', signed=True)
            self.min_frame_size = int().from_bytes(self.raw[4:7], byteorder='big', signed=True)
            self.max_frame_size = int().from_bytes(self.raw[7:10], byteorder='big', signed=True)
            self.sampling_freq = (int().from_bytes(self.raw[10:18], byteorder='big', signed=True) & self.sampling_freq_mask[0]) >> self.sampling_freq_mask[1]
            self.channel = ((int().from_bytes(self.raw[10:18], byteorder='big', signed=True) & self.channel_mask[0]) >> self.channel_mask[1]) + 1
            self.sampling_bit = ((int().from_bytes(self.raw[10:18], byteorder='big', signed=True) & self.sampling_bit_mask[0]) >> self.sampling_bit_mask[1]) + 1
            self.sampling_channel = (int().from_bytes(self.raw[10:18], byteorder='big', signed=True) & self.sampling_channel_mask[0]) >> self.sampling_channel_mask[1]
            self.MD5 = self.raw[18:34].hex()

        def print(self):
            print('Stream Info:')
            print(' min_block_size :', self.min_block_size)
            print(' max_block_size :', self.max_block_size)
            print(' min_frame_size :', self.min_frame_size)
            print(' max_frame_size :', self.max_frame_size)
            print(' Sampling Freq :', self.sampling_freq,'Hz')
            print(' Channel :', self.channel,'channel')
            print(' Sampling bit :', self.sampling_bit,'bit')
            print(' Sampling per channel :', self.sampling_channel)
            print(' Wave MD5 :', self.MD5)
            
    class VorbisComment(object):
        class Tag(object):
            def __init__(self, raw_bytes):
                self.raw = raw_bytes
                self.str = hex2str(self.raw.hex())
                sep_index = self.str.find('=')
                self.key = self.str[0:sep_index]
                self.value = self.str[sep_index + 1 :]
                
        class Edit(object):
            def __init__(self, tags):
                self._tags = tags
                self.is_changed = False

            def change(self, key, value):
                self.is_changed = True
                if key in self._tags:
                    self._tags[key] = value

            def remove(self, key):
                self.is_changed = True
                if key in self._tags:
                    del self._tags[key]

            def add(self, key, value):
                self.is_changed = True
                if key not in self._tags:
                    self._tags[key] = value

            def preview(self):
                if self.is_changed:
                    print('Preview Edited Tags - changed:')
                else:
                    print('Preview Edited Tags - no change:')
                for i in self._tags:
                    print(' %s : %s'%(i, self._tags[i]))

            def save_raw(self):
                raw = len(self._tags).to_bytes(length=4, byteorder='little')
                for i in self._tags:
                    tag_str = i + '=' + self._tags[i]
                    tag_bytes = bytes(tag_str,encoding='utf-8')
                    len_bytes = len(tag_bytes).to_bytes(length=4, byteorder='little')
                    raw += (len_bytes+tag_bytes)
                return raw

        def __init__(self, raw_bytes):
            self.raw = raw_bytes
            self._load_tags()
            
        def _str_(self):
            return json.dumps(self._tags, ensure_ascii = False)

        def _get_tag(self):
            def get_comment_length(raw_bytes):
                return int().from_bytes(raw_bytes, byteorder='little', signed=True)
            tags={}
            point = 0
            length = get_comment_length(self.raw[point:point+4])
            point+=4
            flac_version = hex2str(self.raw[point:point+length].hex())
            point+=length
            tag_number = get_comment_length(self.raw[point:point+4])
            point+=4
            tag_ct = 0
            while tag_ct < tag_number:
                length = get_comment_length(self.raw[point:point+4])
                point += 4
                tag = self.Tag(self.raw[point:point+length])
                tags[tag.key] = tag.value
                tag_ct +=1
                point += length
            return tags, flac_version
        
        def _load_tags(self):
            self._tags, self._flac_version= self._get_tag()
            self.edit = self.Edit(self._tags.copy())
            
        def get(self, key):
            if key in self._tags:
                return self._tags[key]
            else:
                print("file has no tag names %s" % key)
        
        def print(self):
            print('Tags:')
            print(' flac version:', self._flac_version)
            for i in self._tags:
                print(' %s: %s'%(i, self._tags[i]))
                
        def save(self):
            if self.edit.is_changed:
                flac_bytes = bytes(self._flac_version,encoding = 'utf-8')
                flac_len = len(flac_bytes).to_bytes(length = 4,byteorder = 'little')
                raw = flac_len+flac_bytes + self.edit.save_raw()
                self.raw = raw
                self._load_tags()

    class Picture(object):
        picture_type_len = 4
        MIME_type_len_len = 4
        description_len_len = 4
        width_len = 4
        height_len = 4
        color_bit_len = 4
        thumbnail_bit_len = 4
        image_data_len_len = 4
        def __init__(self, raw_bytes, index):
            self._raw = raw_bytes
            self.index = index
            self._load_picture()
            
        def _load_picture(self):
            if len(self._raw) == 0:
                return
            self.raw = self._raw
            self._get_picture_meta_info()
            self.edit = self.Edit(self.image_data,self.picture_type)
            
        def _get_picture_meta_info(self):
            point = 0
            self.picture_type = int().from_bytes(self._raw[point:point+self.picture_type_len], byteorder='big', signed=True)
            point +=self.picture_type_len
            self.MIME_type_len = int().from_bytes(self._raw[point:point+self.MIME_type_len_len], byteorder='big', signed=True)
            point+=self.MIME_type_len_len
            self.MIME_type = hex2str(self._raw[point:point+self.MIME_type_len].hex())
            point+=self.MIME_type_len
            self.description_len = int().from_bytes(self._raw[point:point+self.description_len_len], byteorder='big', signed=True)
            point+=self.description_len_len
            self.description =self._raw[point:point+self.description_len].hex()
            point+=self.description_len
            self.width = int().from_bytes(self._raw[point:point+self.width_len], byteorder='big', signed=True)
            point+=self.width_len
            self.height = int().from_bytes(self._raw[point:point+self.height_len], byteorder='big', signed=True)
            point+=self.height_len
            self.color_bit = int().from_bytes(self._raw[point:point+self.color_bit_len], byteorder='big', signed=True)
            point+=self.color_bit_len
            self.thumbnail_bit = int().from_bytes(self._raw[point:point+self.thumbnail_bit_len], byteorder='big', signed=True)
            point+=self.thumbnail_bit_len
            self.image_data_len = int().from_bytes(self._raw[point:point+self.image_data_len_len], byteorder='big', signed=True)
            point+=self.image_data_len_len
            self.image_data = self._raw[point:point+self.image_data_len]
            
        def print(self):
            print('Image Info - %d'%self.index)
            print(' Picture Type : %2s.%s'%(self.picture_type,PictureType[str(self.picture_type)]))
            print(' Picture Format : %s'%self.MIME_type)
            print(' Picture Size : %d x %d'%(self.width,self.height))
            print(' Color bit : %d'%self.color_bit)
            print(' Picture File Size : %dKB'%math.ceil(len(self.image_data)/1024))
            
        def save_image(self,filename='image.png'):
            with open(filename,'wb') as fp:
                    fp.write(self.image_data)
                    fp.close()
                
        def save(self):
            if self.edit.is_changed:
                #print('save image')
                self._raw = self.edit.edit_buf
                self._load_picture()
                
        def show(self):
            Image.open(BytesIO(self.image_data)).show()

        class Edit(object):

            def __init__(self,image_data,image_type):
                self.is_changed = False
                self.edit_buf = None
                self.image_data = image_data
                self.image_type = image_type


            def replace(self, image, image_type = '', description = ""):
                if image_type == '':
                    image_type = self.image_type
                if type(image) == str:
                    image = Image.open(image)
                    self.edit_buf = get_image_info(image, image_type, description)
                    self.is_changed = True

            def transfer(self, to_format, image_type = "", description = ""):
                image = Image.open(BytesIO(self.image_data))
                if image_type == "":
                    image_type = self.image_type
                if image.format.lower() == to_format.lower():
                    print('Image has already in %s format' % to_format)
                else:
                    image_buf = BytesIO()
                    image.save(image_buf, format = to_format.upper(), quality = 95)
                    image = Image.open(image_buf)
                    self.edit_buf = get_image_info(image, image_type, description)
                    self.is_changed = True

            def remove(self):
                self.is_changed = True
                self.edit_buf = bytes()

    class OtherMeta(object):
        def __init__(self, raw_bytes):
            self.raw = raw_bytes

    def __init__(self,filename):
        self.pictures = []
        self.image_index = 0
        self.is_changed = False
        with open(filename, 'rb') as fp:
            self.raw = fp.read()
        self.path = filename
        self._flac_head = self.raw[0:4]
        self._metablock = []
        self._audio_begin = self._get_meta_block()
        self._audio_frame_raw = self.raw[self._audio_begin:]
        self._blocks = []
        for meta in self._metablock:
            if meta.head.meta_type == 0:
                self.streaminfo = self.StreamInfo(meta.content)
                self._blocks.append([meta.head.meta_type, self.streaminfo])
            elif meta.head.meta_type ==4:
                self.tags = self.VorbisComment(meta.content)
                self._blocks.append([meta.head.meta_type, self.tags])
            elif meta.head.meta_type ==6:
                picture_example = self.Picture(meta.content, self.image_index)
                self.image_index +=1
                self.pictures.append(picture_example)
                self._blocks.append([meta.head.meta_type,picture_example])
            else:
                other_meta_example = self.OtherMeta(meta.content)
                self._blocks.append([meta.head.meta_type,other_meta_example])
        self.picture_number = len(self.pictures)
        self.format = (self.streaminfo.sampling_freq, self.streaminfo.sampling_bit, self.streaminfo.channel)

    def _get_meta_block(self):
        def get_block_length(head_bytes):
            return int().from_bytes(head_bytes[1:4], byteorder='big', signed=True) + 4
        point = 4
        flag = False
        while not flag:
            raw_block_length = get_block_length(self.raw[point:point+4])
            metablock = self.MetaBlock(self.raw[point:point+raw_block_length])
            point+=raw_block_length
            flag = metablock.head.meta_flag
            self._metablock.append(metablock)
        return point

    def add_picture(self,image,image_type = 0, description = ""):
        has_icon1 = False
        has_icon2 = False
        for pic in self.pictures:
            if pic.picture_type == 1:
                has_icon1 = True
            elif pic.picture_type ==2:
                has_icon2 = True
        if image_type == 1 and has_icon1:
            print('Failed: A flac file can only have one 32x32 icon picture!')
            return
        elif image_type == 2 and has_icon2:
            print('Failed: A flac file can only have one file icon picture!')
            return

        image = Image.open(image)
        block = get_image_info(image, image_type, description)
        self.is_changed = True
        index = len(self.pictures)
        picture_block = self.Picture(block, index)
        self.pictures.append(picture_block)
        self._blocks.append([6, picture_block])

    def remove_picture(self, index):
        if index >= len(self.pictures):
            print('Failed : Picture index %d is not existed'%index)
            return
        del self.pictures[index]
        buf = []
        for block in range(len(self._blocks)):
            if not (self._blocks[block][0] == 6 and self._blocks[block][1].index == index):
                buf.append(self._blocks[block])
        self._blocks = buf

    def print(self):
        self.streaminfo.print()
        self.tags.print()
        for pic in self.pictures:
            pic.print()

    def save(self):
        def build_metablock(blocks, last_flag=False):
            if len(blocks[1].raw) == 0:
                return bytes()
            block_byte = bytes()
            if last_flag:
                buf = 0b10000000 + blocks[0]
            else:
                buf = blocks[0]
            buf = buf.to_bytes(length = 1, byteorder = 'big')
            block_byte += buf
            block_byte += len(blocks[1].raw).to_bytes(length = 3, byteorder = 'big')
            #print('head :',block_byte.hex())
            block_byte += blocks[1].raw
            return block_byte
        self.tags.save()
        for pic in self.pictures:
            pic.save()

        raw = self._flac_head
        for block in range(len(self._blocks)):
            if len(self._blocks[block][1].raw) == 0:
                del self._blocks[block]
        for block in range(0,len(self._blocks)-1):
            raw+=build_metablock(self._blocks[block])

        raw+=build_metablock(self._blocks[-1], True)
        raw+=self._audio_frame_raw
        with open(self.path,'wb') as fp:
            fp.write(raw)
        fp.close()


if __name__ == '__main__':
    f = Flac("./1.flac") 
    f.print()
    #print(f.tags)
    #print(f.format)
    #print(f.tags.get('Artist'))
    #f.tags.edit.change('Artist','はな')
    #f.tags.edit.add('Test','123')
    #f.tags.edit.remove('Test')
    #f.pictures[0].edit.replace('Cover.jpg')
    #f.pictures[0].edit.transfer('PNG')
    #f.pictures[0].edit.transfer('JPEG')
    #f.add_picture('Image.png',type)
    #f.remove_picture(index)
    #f.save()
    

