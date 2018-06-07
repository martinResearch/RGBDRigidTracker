# Goal 

the goal of this project is to get an algorithm that can track known rigid objects in a sequence of RGBD (color+depth) images. 

# Method

The rigid object is provided as a three dimensional triangulated surface in the wavefront OBJ files. It is provided in two file: one OPJ file with texture coordinates, and an OBJ file that may not have texture coordinate but has a denser set of vertices (it can be obtained using MeshLab).

In order to generate synthetic RGBD data, we render the textured model in various poses using OpenGL. Using OpenGL we also generate an array that contains the xyz coordinate of the point projecting on each pixel in the camera 3D coordinate system and we generate point clouds in both the point cloud library format and the ptx format (that can be opened in MeshLab).

We then track the rigid object in the sequence of generated point clouds using the Point Cloud Library. We find the pose in the first point cloud using the SampleConsensusInitialAlignmentmethod using FPFHSignature33 Features. Assuming that the object has a only a small displacement between each successive frame, we use the Iterative Closest Point method to refine the pose in each frame using the pose in the previous frame as initialisation. We could use a linear dynamic model to predict the pose from previous frames but this is beyond the scope of this project.


# Compiling the code

* Install the all-in-one installer for the point cloud library version 1.8.1.
* Install cmake (assuming you are in windows)
* use cmake-gui and *surfacematching\pcl\CMakeLists.txt* to generate the visual studio project in the *surfacematching\pcl\build64* folder
* compile and add OpenNI2.dll (from *C:\Program Files\OpenNI2* added by the PCL installer) to the folder containing the executabmle i.e. *pcl\build64\Release*


# Running the code

**Note that this has been tested only on windows**.

You need first to install the python dependencies to generate the synthetic test dataset (see instruction below).
You need to install the Point Cloud Library in order to compile the C++ tracking code.


## Generating RGBD testing images

run the *RGBDSequenceGeneration.py* script in python 

	python RGBDSequenceGeneration.py

this will use OpenGL to generate in the *sequence\crate* subfolder a set of images and point clouds in both the pcd format and ptx formats. You can open the ptx files in MeshLab to visualise the synthesised data. In order to ease visualizatio of the generated data, a animated gif is created.


![image](./images/crate_rgbd.gif)
![image](./images/duck_rgbd.gif)
 
Some alternative method to generate synthetic data could be to use:

 * the PCL method [pcl::RangeImage.createFromPointCloud](http://pointclouds.org/documentation/tutorials/range_image_creation.php). But it would require to generqte a very dense sampling of the surface first.
 *  the PCL's *pcl\_virtual\_scanner\_release.exe* executable with code [here](https://github.com/PointCloudLibrary/pcl/blob/master/tools/virtual_scanner.cpp).  It uses VTK's *vtkCellLocator* function to performe ray / mesh intersections.
 * [render kinect](https://github.com/jbohg/render_kinect). The compilation tested on unbuntu only. It depends on CGAL, OpenCV and some other libraries.
* [blensor](http://www.blensor.org/). It can only be run from within blender, which is not very convenient.
* [CGAL](https://www.cgal.org/) ray/surface intersection methods

## Running the tracking

Once the test data has been generated you can run the tracker on either the duck sequence or the crate sequence using

	runTrackingPCL_Crate.bat
	
	runTrackingPCL_Duck.bat

Each of these two batch file will call the executable surfaceAlign with the right set of parameters.
This will run the executable and open a PCL viewer. You need to press *space* to step from on frame to another. You can use the mouse the turn around the point clouds.

We get the following result on the first frame of each sequence:

![image](./images/pcl_fitting_crate.png)

![image](./images/pcl_fitting_duck.png)

We find the pose in the first point cloud using functions from the  point cloud library. We use the *SampleConsensusInitialAlignment* method with  *FPFHSignature33* Features.
Assuming that the object has a only a small displacement between each successive frame, we use the Iterative Closest Point method to refine the pose in each frame using the pose in the previous frame as initialisation. We could use a linear dynamic model to predict the pose from previous frames but this is beyond the scope of this project.


An alternative method could be to use the *surface_matching* OpenCV contribution available in OpenCV 3.4 described [here](https://docs.opencv.org/3.0-beta/modules/surface_matching/doc/surface_matching.html) inspired from [1], with a python example available [here](https://github.com/opencv/opencv_contrib/tree/master/modules/surface_matching/samples)
In order to get that example running you will need to install the opencv python bindings with the contributions. This method uses [point pair features](https://docs.opencv.org/3.1.0/dc/d9b/classcv_1_1ppf__match__3d_1_1ICP.html). 

Our method do not use the colour information. We could use the method described in [2] to take advantage of the colour. 


## Possible improvements


We do not use the information provided in the RGB image. We could extend our method by detecting interest point in the RGB image.


We convert the model into a point cloud using only the vertices in the OBJ file that contains the densified model. We could keep the triangles information to get a more accurate estimate of the normals and use a point to plan distance in the Iterative Closest Point method.
 


# Installing python Dependencies 

### ModernGL

The synthetic test data in generated using [ModernGL](https://github.com/cprogrammer1994/ModernGL) an easy to use Python OpenGL interface. This allows use the generate texture images and depth range images.
The installation is easy done in the commande line by typing

		pip install ModernGL
		pip install ModerGl.ext.obj
		
In order for the import in python to work, you then may need to go in your *\Lib\site-packages* subfolder in your python distribution and rename the lower case *moderngl* folder into *ModernGL* 
An alternative to using *ModernGL* would by to use *[PyOpenGL](http://pyopengl.sourceforge.net/)*, which follows closely the C interface, or [meshrenderer](https://github.com/BerkeleyAutomation/meshrender) which is build on top of *PyOpenGL* and is designed to make it easy to render images of 3D scenes in pure Python.		

### Pyrr

this is used by ModernGL. install it using 

		pip install pyrr



# Other ressources


### Meshlab resampling

* [MeshLabXml](https://github.com/3DLIRIOUS/MeshLabXML) is a Python (2.7 or 3) scripting interface to MeshLab, the open source system for processing and editing 3D triangular meshes. We could use the *mlx.remesh.uniform_resampling* method to resample the model and get a dense set of points.

### References

[1] *3d object detection and localization using multimodal point pair
  features.* B. Drost and S. Ilic. 2012 Second International Conference on 3D Imaging, Modeling,
  Processing, Visualization Transmission Oct 2012.

[2] *Colored point cloud registration revisited* J. Park, Q.Y. Zhou, and V. Koltun. IEEE International Conference on Computer Vision. Oct 2017.
