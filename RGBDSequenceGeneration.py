# This file contains the code to generate a sequence of simulated RGBD data from an Obj file and a camera sequence
#
# License FreeBSD:
#
# Copyright (c) 2018  Martin de La Gorce
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# The views and conclusions contained in the software and documentation are those
# of the authors and should not be interpreted as representing official policies,
# either expressed or implied, of the FreeBSD Project.

import ModernGL
from ModernGL.ext.obj import Obj
from PIL import Image
from pyrr import Matrix44
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import os
import pointCloudIO
import OpenGLShaders
from scipy.misc import imsave
import copy
import imageio


def generateRGBD(vertex_data,texture_image,modelTransform,imageSize,focal_length,light,idFrame):
    """This function generqtes two numpy arrays, continaining respectively the RGB image and the 3D point cloud scene from the camera"""
    vertex_dataCopy=copy.copy(vertex_data)
    objPoints=np.array(vertex_dataCopy.vert)

    # Context creation
    ctx = ModernGL.create_standalone_context()
    
    # Shaders
    progRGB = ctx.program(vertex_shader=OpenGLShaders.vertex_shader_source, fragment_shader=OpenGLShaders.fragment_shader_RGB_source)
    progXYZ = ctx.program(vertex_shader=OpenGLShaders.vertex_shader_source, fragment_shader=OpenGLShaders.fragment_shader_XYZ_source)
    progDepth= ctx.program(vertex_shader=OpenGLShaders.vertex_shader_source, fragment_shader=OpenGLShaders.fragment_shader_Depth_source)
    
    # Setting up camera
    fov= 2 * np.arctan (imageSize/(focal_length * 2))*180/np.pi
    perspective = Matrix44.perspective_projection(fov, 1.0, 0.1, 1000.0)
    lookat = Matrix44.look_at( (0, 0, 0), (0.0, 0.0, 1), (0.0, 1.0, 0))
    mvp = perspective * lookat
    
    #
    progRGB['Light'].value = light
    progRGB['Color'].value = (1.0, 1.0, 1.0, 0.25)
    progRGB['Mvp'].write(mvp.astype('float32').tobytes())
    progXYZ['Mvp'].write(mvp.astype('float32').tobytes())
 
    
    # Texture   
    texture = ctx.texture(texture_image.size, len(texture_image.split()), texture_image.transpose(Image.FLIP_TOP_BOTTOM).tobytes())
    texture.build_mipmaps()
    
    # moving the mesh using the modelTransform
   
    originalVertices=np.array(vertex_dataCopy.vert)
    newVertices=originalVertices.dot(modelTransform[:3,:3].T)+modelTransform[:3,3][None,:]
    
    # compputing the box around the displaced mesh to get maximum accuracy of the xyz point cloud using unit8 opengl type
    boxmin=np.min(newVertices,axis=0)
    boxmax=np.max(newVertices,axis=0)
    progXYZ['boxmin'].value=tuple(boxmin)
    progXYZ['boxmax'].value=tuple(boxmax)
    vertex_dataCopy.vert=newVertices
        
    vbo = ctx.buffer(vertex_dataCopy.pack())
    vao = ctx.simple_vertex_array(progRGB, vbo, *['in_vert', 'in_text', 'in_norm'])
    vaoXYZ = ctx.simple_vertex_array(progXYZ, vbo, *['in_vert', 'in_text', 'in_norm'])
    
    # Framebuffers
    fbo = ctx.framebuffer(
        ctx.renderbuffer((imageSize, imageSize)),
        ctx.depth_renderbuffer((imageSize, imageSize)),
    )   
    fboXYZ = ctx.framebuffer(     
        ctx.renderbuffer((imageSize, imageSize)),
        ctx.depth_renderbuffer((imageSize, imageSize)),
    )
    
    # Rendering the RGB image
    fbo.use()
    ctx.enable(ModernGL.DEPTH_TEST)
    ctx.clear(0.9, 0.9, 0.9)
    texture.use()
    vao.render()    
    data = fbo.read(components=3, alignment=1)
    img = Image.frombytes('RGB', fbo.size, data, 'raw', 'RGB', 0, -1)
    array_rgb=np.array(img);
    
    # Rendering the XYZ image using OpenGL , limited to 8bit precision for now so we rescale using a bounding 3D box
    fboXYZ.use()
    ctx.enable(ModernGL.DEPTH_TEST)
    ctx.clear(0, 0, 0)
    texture.use()
    vaoXYZ.render()
    data = fboXYZ.read(components=3, alignment=1)
    img = Image.frombytes('RGB', fboXYZ.size, data, 'raw', 'RGB', 0, -1)
    img=np.array(img)
    keep=(img[:,:,0]!=0)|(img[:,:,1]!=0)|(img[:,:,2]!=0)
    array_xyz=np.array(img).astype(np.float32)*((boxmax-boxmin)/255)[None,None,:]+boxmin[None,None,:]; 
    
    # seting background pixels to nan
    array_xyz[~np.tile(keep[:,:,None],[1,1,3])]=np.nan
    
    return array_rgb,array_xyz

def convertToPointCLoud(array_rgb,array_xyz,subsamplingStep):
   
    keep=~np.isnan(array_xyz[:,:,0])
    colors=array_rgb[::subsamplingStep,::subsamplingStep,:].reshape(-1,3)/255.0
    X=array_xyz[::subsamplingStep,::subsamplingStep,0].flatten()
    Y=array_xyz[::subsamplingStep,::subsamplingStep,1].flatten()
    Z=array_xyz[::subsamplingStep,::subsamplingStep,2].flatten()
    keepSubsampled=keep[::subsamplingStep,::subsamplingStep].flatten()
    #colors[:,2]=np.random.rand(colors.shape[0])
    useMatPlotLib=True
    scenePointCloud=np.column_stack((X[keepSubsampled], Y[keepSubsampled], Z[keepSubsampled])).astype(np.float32)
    scenePointCloudColors=colors[keepSubsampled]
    return scenePointCloud,scenePointCloudColors
    
def generateSequence(objFile,texture_image,sequenceFolder):
    
    if not os.path.exists(sequenceFolder):
        os.mkdir(sequenceFolder)
    vertex_data = Obj.open(objFile)
    
    nbFrames=50
    center=np.mean(np.array(vertex_data.vert),axis=0)
    angles=np.array([[-0.3,0.4,-0.4],[-0.3,-0.4,0.4],[-0.3,-0.4,0],[-0.3,0.4,-0.4]])
    anglesInterpolated=np.column_stack([np.interp(np.linspace(0, len(angles)-1,nbFrames), np.arange(len(angles)), angles[:,i]) for i in range(3)])
    translations=np.array([[0,0,3]-center,[0,0.3,3]-center,[0,-0.2,3]-center,[0,0,3]-center])
    translationsInterpolated=np.column_stack([np.interp(np.linspace(0, len(translations)-1,nbFrames), np.arange(len(angles)), translations[:,i]) for i in range(3)])
    light=(-140.0, -300.0, 350.0)
    subsamplingStep=1
    imageSize=300
    focal_length=400    
    imagesRGB = []
    imagesDepth=[]
    pcdFileNames=[]
    maxDepthIntensity=0
	
    for idFrame in range(nbFrames):
        
        modelTransform=np.array(Matrix44.from_eulers(anglesInterpolated[idFrame]))
        modelTransform[:3,3]=translationsInterpolated[idFrame]  
        array_rgb,array_xyz=generateRGBD(vertex_data,texture_image,modelTransform,imageSize,focal_length,light,idFrame)
        imagesRGB.append(array_rgb)
        
        rgbImageName=os.path.join(sequenceFolder,'rgb%03.0d.png'%idFrame)
        imsave(rgbImageName, array_rgb)
        depthImageName=os.path.join(sequenceFolder,'depth%03.0d.png'%idFrame)
        tmp=(1-array_xyz[:,:,2]/np.nanmax(array_xyz[:,:,2]))
        tmp[np.isnan(tmp)]=0
        imsave(depthImageName,np.tile(tmp[:,:,None],[1,1,3]))        
        imagesDepth.append(tmp)
        maxDepthIntensity=max(maxDepthIntensity, np.max(imagesDepth))
        scenePointCloud,scenePointCloudColors=convertToPointCLoud(array_rgb,array_xyz,subsamplingStep)
        pcdFileName=os.path.join(sequenceFolder,'pointCLoud%03.0d.pcd'%idFrame)
        pcdFileRelativePath='pointCLoud%03.0d.pcd'%idFrame
        pcdFileNames.append(pcdFileRelativePath)
        pointCloudIO.savePCD(pcdFileName, None, scenePointCloud.reshape(1,-1,3), 255*scenePointCloudColors.reshape(1,-1,3),format='binary')
        ptxFileName=os.path.join(sequenceFolder,'pointCLoud%03.0d.ptx'%idFrame)
        print('Saving %s'%ptxFileName);
        pointCloudIO.savePTX(ptxFileName,  scenePointCloud.reshape(1,-1,3), 255*scenePointCloudColors.reshape(1,-1,3))

    imageio.mimsave(os.path.join(sequenceFolder,'rgbd_sequence.gif'), [np.column_stack((im[0],(255*np.tile(im[1][:,:,None],[1,1,3])/maxDepthIntensity).astype(np.uint8))) for im in zip(imagesRGB,imagesDepth)]) 
    
    file = open(os.path.join(sequenceFolder,'pcdSequence.txt'),'w')
    for pcdFileName in pcdFileNames:
        file.write(pcdFileName+'\n') 
    file.close()  
	
if __name__ == "__main__":
     
    objFile='data/crate/crate.obj' 
    texture_image = Image.open('data/crate/T_crate1_D.png')
    sequenceFolder='sequence/crate/'
    generateSequence(objFile,texture_image,sequenceFolder)
    
    objFile='data/duck/duck.obj' 
    texture_image = Image.open('data/duck/duckCM.png')
    sequenceFolder='sequence/duck/'
    generateSequence(objFile,texture_image,sequenceFolder)   
