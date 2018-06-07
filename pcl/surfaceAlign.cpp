#include <limits>
#include <fstream>
#include <vector>
#include <Eigen/Core>
#include <pcl/point_types.h>
#include <pcl/point_cloud.h>
#include <pcl/io/pcd_io.h>
#include <pcl/io/ply_io.h>
#include <pcl/io/obj_io.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/filters/passthrough.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/features/normal_3d.h>
#include <pcl/features/fpfh.h>
#include <pcl/registration/ia_ransac.h>
#include <pcl/registration/ia_ransac.h>
#include <pcl/conversions.h>
#include <pcl/registration/icp.h>
#include <pcl/visualization/pcl_visualizer.h>

typedef pcl::PointCloud<pcl::PointXYZ> PointCloud;
typedef pcl::PointCloud<pcl::Normal> SurfaceNormals;
typedef pcl::PointCloud<pcl::FPFHSignature33> LocalFeatures;
typedef pcl::search::KdTree<pcl::PointXYZ> SearchMethod;
bool next_frame = false;
void
keyboardEventOccurred(const pcl::visualization::KeyboardEvent& event,
	void* nothing)
{
	if (event.getKeySym() == "space" && event.keyDown())
		next_frame = true;
}
// Aligns a collection an object templates to a sequence of point clouds
int main(int argc, char **argv)
{
	std::string outputFolder = std::string(argv[3]);
	
	int icpMaxIter = std::stoi(argv[4]);//10
	float voxelGridSize = std::stof(argv[5]);//0.05;
	float minSampleDistance = std::stof(argv[6]);//0.1;
	float maxCorrespondenceDistance = std::stof(argv[7]);//0.05;
	float ICPMaxCorrespondenceDistance = std::stof(argv[8]);//0.03;
	int initMaxIter = std::stoi(argv[9]);//50;
	float RadiusSearch = std::stof(argv[10]);//0.3;
	float featureRadius = std::stof(argv[11]);//0.2;

	if (argc != 12)
	{
		printf("Usage: surfaceAlign.exe model.obj pcdSequence.txt outputFolder icpMaxIter voxelGridSize minSampleDistance maxCorrespondenceDistance ICPMaxCorrespondenceDistance initMaxIter RadiusSearch featureRadius\n");
		return (-1);
	}
	printf("Options:\n", icpMaxIter);
	printf("  outputFolder=%s\n", outputFolder.c_str());
	printf("  icpMaxIter=%d\n", icpMaxIter);
	printf("  voxelGridSize=%f\n", voxelGridSize);
	printf("  minSampleDistance=%f\n", minSampleDistance);
	printf("  maxCorrespondenceDistance=%f\n", maxCorrespondenceDistance);
	printf("  ICPMaxCorrespondenceDistance=%f\n", ICPMaxCorrespondenceDistance);
	printf("  initMaxIter=%d\n", initMaxIter);
	printf("  RadiusSearch=%f\n", RadiusSearch);
	printf("  featureRadius=%f\n", featureRadius);



	// load the model 
	pcl::PolygonMesh modelMesh;
	printf("\nLoading model from %s...", argv[1]);
	pcl::io::loadOBJFile(argv[1], modelMesh);
	PointCloud::Ptr modelPointCloudPtr = PointCloud::Ptr(new PointCloud);
	pcl::fromPCLPointCloud2(modelMesh.cloud, *modelPointCloudPtr);
	printf("done\n");
	printf("Model point cloud size: height=%d width=%d\n", modelPointCloudPtr->height, modelPointCloudPtr->width);

	// Load the point clouds sequence from text file
	std::vector<std::string> pointCloudNames;
	std::ifstream input_stream(argv[2]);
	printf("\nLoading sequence from %s...\n", argv[2]);
	std::string pcd_filename;
	std::string pcdFilePath;
	std::string pcdSequenceName(argv[2]);
	std::size_t botDirPos = pcdSequenceName.find_last_of("/");
	std::string dir = pcdSequenceName.substr(0, botDirPos);
	while (input_stream.good())
	{
		std::getline(input_stream, pcd_filename);
		if (pcd_filename.empty() || pcd_filename.at(0) == '#') // Skip blank lines or comments
			continue;
		pcdFilePath = dir + "/" + pcd_filename;
		pointCloudNames.push_back(pcdFilePath);
	}
	input_stream.close();


	// load the scenes in memory
	std::vector<PointCloud::Ptr> scenesPtr;
	PointCloud scene;

	for (int idFrame = 0; idFrame < pointCloudNames.size(); idFrame++)
	{
		pcdFilePath = pointCloudNames[idFrame];
		printf("Loading %s...", pcdFilePath.c_str());
		scenesPtr.push_back(PointCloud::Ptr(new PointCloud));
		pcl::io::loadPCDFile(pcdFilePath, *scenesPtr[idFrame]);
		printf(" height=%d width=%d\n", scenesPtr[idFrame]->height, scenesPtr[idFrame]->width);
	}


	int idFrame = 0;
	Eigen::Matrix4f transformation;

	// compute features of the model

	printf("\nComputing model point cloud features...");

	pcl::NormalEstimation<pcl::PointXYZ, pcl::Normal> norm_est;


	norm_est.setInputCloud(modelPointCloudPtr);
	SearchMethod::Ptr search_method_ptr = SearchMethod::Ptr(new SearchMethod);
	SurfaceNormals::Ptr normals = SurfaceNormals::Ptr(new SurfaceNormals);
	norm_est.setSearchMethod(search_method_ptr);
	norm_est.setRadiusSearch(RadiusSearch);
	norm_est.compute(*normals);
	LocalFeatures::Ptr modelFeatures = LocalFeatures::Ptr(new LocalFeatures);
	pcl::FPFHEstimation<pcl::PointXYZ, pcl::Normal, pcl::FPFHSignature33> fpfh_est;
	fpfh_est.setInputCloud(modelPointCloudPtr);
	fpfh_est.setInputNormals(normals);
	fpfh_est.setSearchMethod(search_method_ptr);
	fpfh_est.setRadiusSearch(featureRadius);
	fpfh_est.compute(*modelFeatures);
	printf("done\n");

	// The Sample Consensus Initial Alignment (SAC-IA) registration routine and its parameters
	PointCloud::Ptr cloudFinalPtr(new PointCloud);
	pcl::SampleConsensusInitialAlignment<pcl::PointXYZ, pcl::PointXYZ, pcl::FPFHSignature33> sac_ia_;
	sac_ia_.setMinSampleDistance(minSampleDistance);
	sac_ia_.setMaxCorrespondenceDistance(maxCorrespondenceDistance);
	sac_ia_.setMaximumIterations(initMaxIter);


	// initialization in first frame
	printf("Reducing scene cloud size...");
	pcl::VoxelGrid<pcl::PointXYZ> vox_grid;
	vox_grid.setInputCloud(scenesPtr[idFrame]);
	vox_grid.setLeafSize(voxelGridSize, voxelGridSize, voxelGridSize);
	//vox_grid.filter (*cloud); // Please see this http://www.pcl-developers.org/Possible-problem-in-new-VoxelGrid-implementation-from-PCL-1-5-0-td5490361.html
	PointCloud::Ptr reducedCloud(new PointCloud);
	vox_grid.filter(*reducedCloud);
	printf("done. Reduced from %d to %d points\n", scenesPtr[idFrame]->height*scenesPtr[idFrame]->width, reducedCloud->height*reducedCloud->width);
	pcl::io::savePLYFileBinary(outputFolder + "/" + "reducedScene0.ply", *reducedCloud);

	printf("Computing scene point cloud features...");
	pcl::NormalEstimation<pcl::PointXYZ, pcl::Normal> scene_norm_est;
	scene_norm_est.setInputCloud(reducedCloud);
	SurfaceNormals::Ptr scene_normals = SurfaceNormals::Ptr(new SurfaceNormals);
	scene_norm_est.setSearchMethod(search_method_ptr);
	scene_norm_est.setRadiusSearch(RadiusSearch);
	scene_norm_est.compute(*scene_normals);
	LocalFeatures::Ptr scene_features = LocalFeatures::Ptr(new LocalFeatures);
	pcl::FPFHEstimation<pcl::PointXYZ, pcl::Normal, pcl::FPFHSignature33> scene_fpfh_est;
	scene_fpfh_est.setInputCloud(reducedCloud);
	scene_fpfh_est.setInputNormals(scene_normals);
	scene_fpfh_est.setSearchMethod(search_method_ptr);
	scene_fpfh_est.setRadiusSearch(featureRadius);
	scene_fpfh_est.compute(*scene_features);
	printf("done\n");

	printf("Initialisation using SampleConsensusInitialAlignment method...");
	sac_ia_.setInputTarget(reducedCloud);
	sac_ia_.setTargetFeatures(scene_features);
	sac_ia_.setInputSource(modelPointCloudPtr);
	sac_ia_.setSourceFeatures(modelFeatures);
	//sac_ia_.setInputSource(reducedCloud);
	//sac_ia_.setSourceFeatures(scene_features);
	//sac_ia_.setInputTarget(modelPointCloudPtr);
	//sac_ia_.setTargetFeatures(modelFeatures);

	printf("\n");
	sac_ia_.align(*cloudFinalPtr);
	float fitness_score = (float)sac_ia_.getFitnessScore(maxCorrespondenceDistance);
	transformation = sac_ia_.getFinalTransformation();
	printf("done.\nScore = %f: \n ", fitness_score);
	std::cout << transformation << std::endl;


	// Visualization
	pcl::visualization::PCLVisualizer viewer("range tracking demo");
	// Create two vertically separated viewports
	int v1(0);

	viewer.createViewPort(0.0, 0.0, 1, 1.0, v1);


	// The color we will be using
	float bckgr_gray_level = 0.0;  // Black
	float txt_gray_lvl = 1.0 - bckgr_gray_level;

	// Scene point in green
	pcl::visualization::PointCloudColorHandlerCustom<pcl::PointXYZ> cloudScene_color_h(scenesPtr[0], 0, 255, 0);
	viewer.addPointCloud(scenesPtr[0], cloudScene_color_h, "scene", v1);
	viewer.setPointCloudRenderingProperties(pcl::visualization::PCL_VISUALIZER_POINT_SIZE, 3, "scene");
	//viewer.addPointCloud(cloud_in, cloud_in_color_h, "cloud_in_v2", v2);


	// Set background color
	viewer.setBackgroundColor(bckgr_gray_level, bckgr_gray_level, bckgr_gray_level, v1);


	// ICP aligned point cloud is red
	pcl::visualization::PointCloudColorHandlerCustom<pcl::PointXYZ> cloudFinal_color_h(cloudFinalPtr, 180, 20, 20);
	viewer.addPointCloud(cloudFinalPtr, cloudFinal_color_h, "cloud fitted", v1);
	viewer.setPointCloudRenderingProperties(pcl::visualization::PCL_VISUALIZER_POINT_SIZE, 3, "cloud fitted");
	viewer.addCoordinateSystem(1.0);
	viewer.initCameraParameters();
	// Register keyboard callback :
	viewer.registerKeyboardCallback(&keyboardEventOccurred, (void*)NULL);

	// tracking

	pcl::IterativeClosestPoint<pcl::PointXYZ, pcl::PointXYZ> icp;

	pcl::io::savePLYFileBinary(outputFolder + "/" + "initialFit.ply", *cloudFinalPtr);
	// Set camera position and orientation
	viewer.setCameraPosition(0, 0, -2, 0, 1, 0, 0);
	viewer.setSize(1280, 1024);  // Visualiser window size

	printf("Press space to continue");

	idFrame = 0;

	icp.setMaxCorrespondenceDistance(ICPMaxCorrespondenceDistance);
	icp.setMaximumIterations(icpMaxIter);
	icp.setInputTarget(modelPointCloudPtr);

	PointCloud::Ptr alignedScene(new PointCloud);
	PointCloud::Ptr alignedModel(new PointCloud);

	Eigen::Matrix4f sceneTransformation = transformation.inverse();
	while (!viewer.wasStopped())
	{
		viewer.spinOnce();

		// The user pressed "space" :
		if (next_frame)
		{
			if (idFrame == pointCloudNames.size())
			{
				break;
			}
			// The Iterative Closest Point algorithm
			cloudScene_color_h.setInputCloud(scenesPtr[idFrame]);
			viewer.updatePointCloud(scenesPtr[idFrame], cloudScene_color_h, "scene");
			printf("Refining pose in frame %d using ICP....", idFrame);

			icp.setInputSource(scenesPtr[idFrame]);
			icp.align(*alignedScene, sceneTransformation);
			std::cout << "has converged:" << icp.hasConverged() << " score: " << icp.getFitnessScore() << std::endl << std::endl;
			sceneTransformation = icp.getFinalTransformation();
			std::cout << sceneTransformation.inverse() << std::endl;
			pcl::transformPointCloud(*modelPointCloudPtr, *alignedModel, sceneTransformation.inverse());
			viewer.updatePointCloud(alignedModel, cloudFinal_color_h, "cloud fitted");
			// Save the aligned template for visualization
			pcl::io::savePLYFileBinary(outputFolder+"/"+"aligned" + std::to_string(idFrame) + ".ply", *alignedModel);
			idFrame++;

			printf("Press space to continue");
		}
		next_frame = false;
	}


	printf("Tracking done");
	return (0);
}