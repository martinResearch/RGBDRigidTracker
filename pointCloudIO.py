import numpy as np
#from  camera import RigidTransform3D

def savePTX(filename,points,colors=None,transformMtx=None):
	"""export data to the leica ptx format
	this format assumes that x is pointing up, 	
	The points are listed one column after another from left to right and from top to botom in each column i.e
	1 4 7 
	2 5 8
	3 6 9
	"""
	if transformMtx is None:
		transformMtx=np.column_stack((np.eye(3),np.zeros((3,1))))
	pointsInScannerCoordinateSystem=(points-transformMtx[:,3]).dot(transformMtx[:3,:3].T)# the ptx format seems to have the convention that the point are goiven in the scaner coordinate system
	with open(filename, 'w') as f:
		assert points.shape[2]==3
		f.write(str(points.shape[1])+'\n')
		f.write(str(points.shape[0])+'\n')
		np.savetxt(f,transformMtx[:,3].reshape([1,3]),'%.5f')
		np.savetxt(f,transformMtx[:3,:3].T,'%.5f')
		M=np.zeros((4,4))
		M[3,3]=1
		M[:3,:3]=transformMtx[:3,:3].T
		np.savetxt(f,M,'%.5f')
		if colors is None:
			colors=np.ones((points.shape[0],points.shape[1],3),dtype=np.uint8)*np.array([127,127,127])
		p=np.dstack((np.flipud(pointsInScannerCoordinateSystem),np.ones((points.shape[0],points.shape[1],1),dtype=np.uint8),np.flipud(colors)))
		np.savetxt(f,np.transpose(p,[1,0,2]).reshape(-1,7),'%.5f %.5f %.5f %d %d %d %d')



def loadPTX(filename,transform_the_points=True):
	with open(filename, 'r') as f:

		nbcols=int(f.readline())
		nblines=int(f.readline())
		#print (nblines)
		#print (nbcols)

		#np.loadtxt does not allow yet to specify a number of rows, np ticket 1731.
		#http://np-discussion.10968.n7.nabble.com/using-loadtxt-for-given-number-of-rows-td3635.html
		translation=np.fromfile(f, sep=' ', count=3)
		rotation=np.fromfile(f, sep=' ', count=9).reshape(3,3).T
		print (rotation)
		M=np.fromfile(f, sep=' ', count=16).reshape(4,4)		
		#transform=RigidTransform3D(rotation,translation,fix_rotation=True)
		data=np.fromfile(f,  sep=' ',count=-1)
		points_with_color=data.reshape(-1,7)
		pointsInScannerCoordinateSystem=np.transpose(points_with_color[:,:3].reshape((nbcols,nblines,3)),[1,0,2])[::-1,:,:]
		if transform_the_points:
			points=transform.apply(pointsInScannerCoordinateSystem)# the ptx format seems to have the convention that the point are goiven in the scaner coordinate system
		else: 
			points=pointsInScannerCoordinateSystem
		colors=np.transpose(points_with_color[:,4:7].reshape((nbcols,nblines,3)).astype(int),[1,0,2])[::-1,:,:]

		return points, colors , transform

def savePCD(filename,transform,points,colors, data=None,format='ascii'):
	"""export data to the Point Cloud Library PCD format
	the file can then be visualized using the pcl executable pcd_viewer that can be called from the terminal
	there seem to be a problem with the exportation of the point colors..."""
	
	
	fields_str = 'x y z rgb'
	type   = 'F F F F'
	count  = '1 1 1 1'
	size   = '4 4 4 4' 

	if data:
		for k in data.keys():
			assert(k.find(' ')==-1)		
		fields_str+=' '+ ' '.join(data.keys())	
		typeconversion=dict()
		typeconversion[np.float32]=('F',4)
		typeconversion[np.uint32]=('U',4)
		typeconversion[np.int32]=('I',4)		
		typeconversion[np.uint8]=('U',1)	
		typeconversion[np.uint16]=('U',2)		
		type+=' '+' '.join([typeconversion[d.dtype.type][0] for d in data.itervalues()])
		size+=' '+' '.join([str(typeconversion[d.dtype.type][1]) for d in data.itervalues()])
		count+=' 1'*len(data.keys())
	
	with open(filename, 'w') as f:
		f.write('# .PCD v0.7 - Point Cloud Data file format\n')
		f.write('VERSION 0.7\n')
		f.write('FIELDS '+fields_str+'\n')
		f.write('SIZE '  +size  +'\n')
		f.write('TYPE '  +type  +'\n')
		f.write('COUNT ' +count  +'\n')
		f.write('WIDTH '+str(points.shape[1])+'\n')
		f.write('HEIGHT '+str(points.shape[0])+'\n')
		f.write('VIEWPOINT ')
		if transform:
			np.savetxt(f,transform.get_translation().reshape([1,3]),'%.5f',newline='')
		else:
			np.savetxt(f,np.zeros((3)).reshape([1,3]),'%.5f',newline='')
		quaternion=np.array([1,0,0,0])# could use the thirdparty module transomartions.py by christoph gohlke
		f.write(' ')
		np.savetxt(f,quaternion.reshape(1,4),'%.5f',newline='')			
		f.write('\n')
		f.write('POINTS '+str(points.shape[0]*points.shape[1])+'\n')

		#for  key, value in idlabelToMaterial.iteritems():
		#	f.write('# material '+str(key)+' = '+value+'\n')
		
		
		
		#convert rgb clors to the weird float format
		colors_unint32=colors.astype(np.uint32)
		rgb_int = (colors_unint32[:,:,0] << 16) | (colors_unint32[:,:,1] << 8) | (colors_unint32[:,:,2])
		s=np.ndarray.tostring(rgb_int)
		colors_float=np.fromstring(s,dtype=np.float32).reshape((colors.shape[0],colors.shape[1]))
				
			
		if format=='ascii':
			f.write('DATA ascii\n')
			for i in range(points.shape[0]):
				for j in range(points.shape[1]):
					p=points[i,j]
					
					rgb_string= "%.8e"%	colors_float[i,j]
					s='%.7f'%p[0]+' '+'%.7f'%p[1]+' '+'%.7f'%p[2]+' '+rgb_string
					if data:
						for k in data.keys():
							s+=' '+str(data[k][i,j])
					f.write(s+'\n')	
		elif format=='binary':
			f.write('DATA binary\n')
			if data is not None:
				nptypes=[np.float32]*4+[d.dtype.type for d in data.itervalues()]
				fieldnames=['x','y','z','rgb']+data.keys()
				
			else:
				nptypes=[np.float32]*4
				fieldnames=['x','y','z','rgb']
			dt = np.dtype(list(zip(fieldnames,nptypes)))	
			DataArray=np.empty((points.shape[0],points.shape[1]),dtype=dt)
			DataArray['x']=points[:,:,0]
			DataArray['y']=points[:,:,1]
			DataArray['z']=points[:,:,2]
			DataArray['rgb']=colors_float
			if data is not None:
				for k in data.keys():
					DataArray[k]=data[k]
			DataArray.tofile(f)
		else:
			print( "unkown format")
			raise
		


def loadPCD(filename,default_color=[128,128,128]):
	header_dict=dict()
	maps=dict()
	with open(filename, 'r') as f:
		while True:
			line=f.readline()
			line = line.rstrip('\n')
			line = line.rstrip('\r')
			t=line.split(' ')
			if t[0][0]=='#':
				if t[1]=='map:': # this is not part of the PCD format , but is a custom way to save some information
					e=t[3].split(':')
					if not(t[2] in maps):
						maps[t[2]]=dict()
					maps[t[2]][int(e[0])]=e[1]
				else:
					continue
			if t[0]=='DATA':
				datatype=t[1]
				break
			else :
				header_dict[t[0]]=t[1:]

		#Data=numpy.empty((header_dict['WIDTH'],header_dict['HEIGHT']),dtype=float)
		nbPoints=int(header_dict['POINTS'][0])


		py_types=[]
		for field,type,size,count in zip(header_dict['FIELDS'],header_dict['TYPE'],header_dict['SIZE'],header_dict['COUNT']):
			
			if type=='F':
				if size=='4':
					py_type=np.float32
				else:
					print ('not coded yet')
			elif  type=='U':
				if size=='4':
					py_type=np.uint32
				elif size=='1':
					py_type=np.uint8
				elif size=='2':
					py_type=np.uint16
				else:
					print ('not coded yet')
			elif  type=='I':
				if size=='4':
					py_type=np.int32
				else:
					print( 'not coded yet')
			py_types.append(py_type)		
		dt = np.dtype(list(zip(header_dict['FIELDS'],py_types)))
		Data=dict()
		if datatype=='ascii':
			DataArray=np.fromfile(f,  sep=' ',count=-1).reshape(nbPoints,-1)

			nbFields=len(header_dict['FIELDS'])
			col=0	
			for field,py_type,count in zip(header_dict['FIELDS'],py_types,header_dict['COUNT']):	
				if int(count)>1:
					Data[field]=DataArray[:,col:col+int(count)].astype(py_type)
				else:
					Data[field]=DataArray[:,col].astype(py_type)
				col+=int(count)			
		elif  datatype=='binary':	
			DataArray=np.fromfile(f, dtype=dt,count=nbPoints)
			for key in header_dict['FIELDS']:
				Data[key]=DataArray[key]
		elif datatype=='binary_compressed':
			print ('not yet coded looking at http://www.mathworks.fr/matlabcentral/fileexchange/40382-matlab-to-point-cloud-library/ it seem like it used lzf compression so we could use https://pypi.python.org/pypi/python-lzf')
			raise
		else:
			print ('loading type '+ datatype+' not yet coded')
			raise

		if ('x' in Data) and ('y' in Data) and ('y' in Data):
			points=np.column_stack ((Data['x'],Data['y'],Data['z'])).reshape(int(header_dict['HEIGHT'][0]),int(header_dict['WIDTH'][0]),-1)
		else:
			points=[]		
		colors=np.empty((nbPoints,3),dtype=np.uint8)
		from struct import pack,unpack
		if 'rgb' in Data:
			s=np.ndarray.tostring(np.array(Data['rgb']))
			rgb_int=np.fromstring(s,dtype=np.int32)

				#from http://www.pointclouds.org/documentation/tutorials/adding_custom_ptype.php:
				# "The reason why rgb data is being packed as a float comes from the early development
				#o f PCL as part of the ROS project, where RGB data is still being sent by wire as 
				#float numbers. We expect this data type to be dropped as soon as all legacy code has 
				#been rewritten (most likely in PCL 2.x).
			colors=np.column_stack(((rgb_int>>16)& 0x0000ff,(rgb_int>>8)& 0x0000ff,(rgb_int)& 0x0000ff))
			del Data['rgb']
		elif   'rgba' in Data:
			print ('not et coded')
			colors[:,0].fill(default_color[0])
			colors[:,1].fill(default_color[1])
			colors[:,2].fill(default_color[2])			
		else:
			colors[:,0].fill(default_color[0])
			colors[:,1].fill(default_color[1])
			colors[:,2].fill(default_color[2])
		if  'normal_x' in Data:
			Data['normals']=np.column_stack ((Data['normal_x'],Data['normal_y'],Data['normal_z'])).reshape(int(header_dict['HEIGHT'][0]),int(header_dict['WIDTH'][0]),-1)

		for key in ['x','y','z']:
			if key in Data:
				del Data[key]
		return points,colors, Data,maps

def loadOFF(filename):
	point=None
	with open(filename, 'r') as f:
		line=f.readline().rstrip('\n')
		assert(line=='OFF')
		line=f.readline().rstrip('\n')
		t=line.split(' ')	
		nb_vertices=int(t[0])
		nb_faces=int(t[1])
		nb_lines=int(t[2])

		points=np.fromfile(f,  sep=' ',count=nb_vertices*3).reshape(nb_vertices,3)
	return points


def loadPLY(filename,getFaces=True):
	header_dict=dict()
	with open(filename, 'r') as f:
		line=f.readline().rstrip('\n')
		assert(line=='ply')
		line=f.readline().rstrip('\n')
		assert(line=='format ascii 1.0')
		fields_vertex_names=[]
		fields_vertex_types=[]
		fields_face_names=[]
		fields_face_types=[]	
		fields_edges_names=[]
		fields_edges_types=[]			
		nbFaces=0
		nbEdges=0
		while True:
			line=f.readline()
			line = line.rstrip('\n')
			t=line.split(' ')

			if t[0]=='comment':
				continue
			elif t[0]=='end_header':
				break
			elif t[0]=='property':
				if t[1]=='list':
					fields_names.append(t[4])
					fields_types.append(t[1:4])
				else:
					fields_names.append(t[2])
					fields_types.append(t[1])
			elif t[0]=='element':
				if t[1]=='vertex':
					nbPoints=int(t[2])
					fields_names=fields_vertex_names
					fields_types=fields_vertex_types	
					assert(len(t)==3)
				if t[1]=='face':
					nbFaces=int(t[2])
					fields_names=fields_face_names
					fields_types=fields_face_types	
				if t[1]=='edge':
					nbEdges=int(t[2])
					fields_names=fields_edges_names
					fields_types=fields_edges_types				
			else:
				print ('unkown key word')

		nbVertexFields=len(fields_vertex_names)
		DataArray=np.fromfile(f,  sep=' ',count=nbPoints*nbVertexFields).reshape(nbPoints,-1)

		Data=dict()

		for i,field,type in zip(range(nbVertexFields),fields_vertex_names,fields_vertex_types):
			if type=='float':
				py_type=np.float32
			elif  type=='uint':
				py_type=np.uint32
			elif  type=='uchar':
				py_type=np.uint16 #uint8
			else:
				print ('not yet coded')
				raise

			Data[field]=DataArray[:,i].astype(py_type)

		points=np.column_stack ((Data['x'],Data['y'],Data['z']))
		for key in ['x','y','z']:
			del Data[key]		
		if ('red' in Data) and ('green' in Data) and ('blue' in Data):
			colors=np.column_stack ((Data['red'],Data['green'],Data['blue']))
			for key in ['red','green','blue']:
				del Data[key]			
		else: 
			colors=None

		if getFaces:
			edges=None
			DataFaces=dict()
			DataPolylines=dict()
			for field in fields_face_names[1:]:
				DataFaces[field]=[]#np.empty((nbFaces),dtype=np.uint32)
				DataPolylines[field]   =[]
			if nbFaces>0:
				polylines=[]
				faces=[]
				for idface in range(nbFaces):
					line=f.readline()
					line = line.rstrip('\n')
					t=[i for i in line.split(' ')]
					for i in range(3,int(t[0])+1):
						faces.append([int(t[1]),int(t[i-1]),int(t[i])])
						for id,field in enumerate(fields_face_names[1:]):
							#fields_face_names
							DataFaces[field].append(float(t[int(t[0])+id+1]))
					polylines.append(points[[int(x) for x in  t[1:int(t[0])+1]]])
					for id,field in enumerate(fields_face_names[1:]):
							#fields_face_names
						DataPolylines[field].append(float(t[int(t[0])+id+1]))
						#DataPolylines[field]=
				for field in (fields_face_names[1:]):
					DataFaces[field]=np.array(DataFaces[field])
				faces=np.array(faces,dtype=np.int32)

			else: 
				faces=None
				DataFaces=None
				polylines=None
				edges=None
			if nbEdges>0:
				data=np.fromfile(f,  sep=' ',count=nbEdges*2)
				edges=data.reshape(nbEdges,2)
			return points,colors, Data,faces,DataFaces,polylines,edges,DataPolylines
		else:
			return points,colors, Data
if __name__ == "__main__":
	points,colors, transform,maps=loadPCD('data/scan_ascii.pcd')
	from matplotlib import pyplot as plt
	from mpl_toolkits.mplot3d import Axes3D
	fig = plt.figure()
	ax = Axes3D(fig)
	points2=points.reshape(-1,3)
	ax.scatter(points2[:,0],points2[:,1],points2[:,2],s=20)
	plt.show()