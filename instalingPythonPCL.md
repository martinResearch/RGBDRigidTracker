### Point Cloud Library with Python binding

If you want to test the code based on the Point Cloud LIbrary you will have to install the PCL library and the [PCL python bindings](http://strawlab.github.io/python-pcl/) provided by strawlab.
Unfortunalty there is no python package with one-liner installation command using pip.
You will need to follow the installation steps described [here](http://strawlab.github.io/python-pcl/). 

**Note that the Point Cloud library is quite a large library when installed with its dependencies (OpenNI,VTK,GoogleTest,Boost,Eigen,FLANN,Qhull,Qt) and takes about 4Go on the drive.**

I have
 
* Microsoft Visual Studio 2017
* Microsoft SDK v7.1A
* Windows Kits 10

I did not install the  Visual Studio 2015 C++ Compiler Tools. The link provided on [https://github.com/strawlab/python-pcl](https://github.com/strawlab/python-pcl) is broken. The solution is to 
install visual studio build tool 2017 and check SDK 2015 during the installation. 

I had to do those steps

* download the all in one PCL installer (i used  PCL-1.8.1-AllInOne-msvc2017-win64.exe) and install it
* add the environemetn variables
 
        PCL_ROOT
            C:\Program Files\PCL 1.8.1
        PATH
			C:\Program Files\OpenNI2\Tools;
			C:\Program Files (x86)\Windows Kits\10\bin\10.0.15063.0\x64
			C:\Program Files\OpenNI2;
			C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC\14.14.26428\bin\Hostx64\x64

* install gtk+  (a cross plateform GUI framework) for windows (to get pkg-config.exe). used http://win32builder.gnome.org/gtk+-bundle_3.10.4-20131202_win64.zip. i did not add C:\Program Files\gtk+\bin to the path, not sure why

		

* In the command line , move in the folder containing the clone of python_pcl 
	
		python setup.py build_ext -i
		python setup.py install



