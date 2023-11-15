from PIL import Image
import numpy as np
import os
import re
import sys, argparse


def read_file_bytes(path):
    with open(path, 'rb') as f:
        bytes_ = f.read()
    return bytes_

def write_file_bytes(path, bytes2write):
    with open(path, 'wb') as f:
        f.write(bytes2write)

class HideOnImage:
    def __init__(self, finalCode=None, verbose=False):
        if finalCode is None:
            self.finalCode = b'<END>'
        else:
            self.finalCode = finalCode
        self.verbose = verbose
        self.pathWrite = None
        self.imagesPath = None
        self.bytes2hide = None
        self.filenames = None
        self.dims = None
        self.images = None
        self.usedImages = None
        self.secretImages = None
        self.secretImages = None
        
    def load_images(self, imagesPath):
        self.imagesPath = imagesPath
        supportedFormats = ['jpg', 'jpeg', 'png', 'bmp']
        filFormats = '(.'+'$)|(.'.join(supportedFormats)+'$)'
        images = sorted(os.listdir(imagesPath))
        images = [Image.open(os.path.join(imagesPath, img)) for img in images 
                  if re.search(filFormats, img)]
        self.filenames = [img.filename.split('/')[-1] for img in images]
        if self.verbose:
            print('Images loaded: \n' + 
                  '\n'.join(self.filenames))
        self.images = [np.array(img.convert('RGB'), dtype='uint8') 
                       for img in images]
        self.dims = [img.shape for img in self.images]
        return self.images
    
    def _test_msg_fits_in_imgs(self,):
        bytes2hide = self.bytes2hide + self.finalCode
        bytes2hide = ''.join([format(b, '08b') for b in bytes2hide])
        msgLen = len(bytes2hide)
        imagesLen = len(
            np.concatenate([img.flatten() for img in self.images]).flatten()
                     )
        if imagesLen < msgLen:
            pct = round(imagesLen/msgLen * 100, 2)
            raise Exception(
                'The total length of the images is insufficient to hide the ' +
                f'message (you need {msgLen - imagesLen:,} bytes more).\n' +
                f'Try loading more images. ' +
                f'Percentage of the message hidden: {pct}%')
    
    def hide_msg_in_imgs(self, images, bytes2hide):
        bytes2hide += self.finalCode
        bytes2hide = ''.join([format(b, '08b') for b in bytes2hide])
        self.usedImages = []
        self.secretImages = []
        for i, image in enumerate(images):
            imageBits = [format(b, '08b') for b in image.flatten().tobytes()]
            secretImage = []
            bitsIterable = zip(bytes2hide, imageBits)
            for msgBit, imageByte in bitsIterable:
                secretImage.append(imageByte[:-1] + msgBit)
            if len(bytes2hide) < len(imageBits):
                secretImage += imageBits[len(bytes2hide):]
            secretImage = [int(b, 2) for b in secretImage]
            secretImage = np.array(
                secretImage, dtype='uint8'
                ).reshape(self.dims[i])
            self.secretImages.append(secretImage)
            self.usedImages.append(self.filenames[i])
            if len(bytes2hide) > len(imageBits):
                bytes2hide = bytes2hide[len(imageBits):]
            else:
                return self.secretImages
            
    def save_images(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
        for i, img in enumerate(self.secretImages):
            secretImg = Image.fromarray(img)
            imageName = self.usedImages[i].split('.')[0]
            imageName = imageName+'.png'
            secretImg.save(
                os.path.join(path, imageName),
                optimize=False,
                compress_level=0
                )
            
    def hide_and_save(self, pathRead, bytes2hide, pathWrite=None):
        if pathWrite is None:
            self.pathWrite = os.path.join(pathRead, 'secret')
        else:
            self.pathWrite = pathWrite
        self.imagesPath = pathRead
        self.bytes2hide = bytes2hide
        self.filenames = None
        self.dims = None
        self.images = self.load_images(pathRead)
        self._test_msg_fits_in_imgs()
        self.usedImages = None
        self.secretImages = None
        self.secretImages = self.hide_msg_in_imgs(self.images, self.bytes2hide)
        self.save_images(self.pathWrite)
        
    def read_hidden_bits(self, imagesPath):
        self.images = imagesPath
        self.images = self.load_images(imagesPath)
        bytes2hide = b''
        for image in self.images:
            imageBits = [format(b, '08b') for b in image.flatten().tobytes()]
            for i in range(0, len(imageBits), 8):
                bits = [b[-1] for b in imageBits[i:i+8]]
                bytes2hide += bytes([int(''.join(bits), 2)])
                if bytes2hide[-len(self.finalCode):] == self.finalCode:
                    self.bytes2hide = bytes2hide[:-len(self.finalCode)]
                    return self.bytes2hide


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(
        description="Hide bytes on media files."
    )
    argParser.add_argument(
        'type',
        choices=['image', 'audio'], 
        help='image or audio',
        )
    argParser.add_argument(
        'mode',
        choices=['hide', 'read'],
        help='If image: hide (to hide on images) or ' +
        'read (to read hidden bytes from images)',
        )
    argParser.add_argument(
        "-ip", "--imagePath", help="Image folder", required=True
    )
    argParser.add_argument(
        "-if", "--inputFile", help="Input file to hide", required=False
    )
    argParser.add_argument(
        "-fc", "--finalCode", help="Code to stop reading hidded bytes in images",
        required=False
        )
    argParser.add_argument(
        "-op", "--outputPath", help="Output path to save the images with the " +
        "hidden message (if hide mode) or output file path to save the hidden " + 
        "bytes (if read mode)",
        required=False
        )
    argParser.add_argument(
        "-v", "--verbose", help="Show logs", action='store_true',
        required=False
        )
    args = argParser.parse_args()
    
    if args.type == 'image':
        if args.finalCode is not None:
            finalCode = args.finalCode.encode()
        else:
            finalCode = None
        hideImage = HideOnImage(
            verbose=args.verbose,
            finalCode=finalCode
            )
        if args.mode == 'hide':
            bytes2hide = read_file_bytes(args.inputFile)
            hideImage.hide_and_save(
                pathRead=args.imagePath, 
                bytes2hide=bytes2hide,
                pathWrite=args.outputPath)
        elif args.mode == 'read':
            hiddenBytes = hideImage.read_hidden_bits(
                imagesPath=args.imagePath
            )
            write_file_bytes(args.outputPath, hiddenBytes)
