#!/usr/bin/env python
import gcSupport, sys, os, gzip, xml.dom.minidom
from grid_control import *

def main(args):

	if len(args) == 3:
		(jobid, wmsid, retcode) = args
		if retcode != '0':
			sys.exit(0)
		workDir = os.environ['GC_WORKDIR']
		jobList = [ jobid ]
	else:
		(workDir, jobList) = gcSupport.getWorkJobs(args)
	jobList = map(int, jobList)

	# Lock file in case several instances of this program are running
	mutex = gcSupport.FileMutex(os.path.join(workDir, 'datasetCacheAdd.lock'))

	try:
		taskInfo = utils.PersistentDict(os.path.join(workDir, 'task.dat'), ' = ')
		provider = DataProvider.loadState(gcSupport.ConfigDummy(), workDir, 'production.dbs')

		# Try to read all existing Blocks from production.dbs
		try:
			quiet = gcSupport.Silencer()
			blocks = provider.getBlocks()
		except:
			blocks = []
		del quiet

		for jobNum in jobList:
			outputDir = os.path.join(workDir, 'output', 'job_' + str(jobNum))

			# Read the file hash entries from job info file
			files = gcSupport.getFileInfo(workDir, jobNum, lambda retCode: retCode == 0, rejected = [])
			for (hash, name_local, name_dest, pathSE) in files:
				dataset = "/PRIVATE/%s" % (name_local.replace('.root', ''))
				blockname = "%s-%05d" % (taskInfo['task id'][2:], int(os.environ.get('GC_PARAM_ID', 0)))

				# Try to find block with given dataset + blockname
				cblock = None
				for block in blocks:
					if (block[DataProvider.Dataset] == dataset) and (block[DataProvider.BlockName] == blockname):
						cblock = block
				# No block found => Create new block
				if cblock == None:
					cblock = {
						DataProvider.Dataset: dataset,
						DataProvider.BlockName: blockname,
						DataProvider.NEvents: 0,
						DataProvider.SEList: None,
						DataProvider.FileList: []
					}
					blocks.append(cblock)

				lfn = os.path.join(pathSE, name_dest)
				nEvents = 0

				# Read framework report files to get number of events
				tarFile = tarfile.open(os.path.join(outputDir, "cmssw.dbs.tar.gz"), "r:gz")
				fwkReports = filter(lambda x: os.path.basename(x.name) == 'report.xml', tarFile.getmembers())
				try:
					for fwkReport in map(lambda fn: tarFile.extractfile(fn), fwkReports):
						for outFile in xml.dom.minidom.parse(fwkReport).getElementsByTagName("File"):
							pfn = outFile.getElementsByTagName("PFN")[0].childNodes[0].data
							if pfn == name_local:
								nEvents = int(outFile.getElementsByTagName("TotalEvents")[0].childNodes[0].data)
				except:
					print "Error while parsing framework output!"
					return 0

				if nEvents == 0:
					continue

				# Add file to filelist of the current block
				filelist = cblock[DataProvider.FileList]
				if not lfn in map(lambda x: x[DataProvider.lfn], filelist):
					filelist.append({ DataProvider.lfn: lfn, DataProvider.NEvents: nEvents })
				cblock[DataProvider.NEvents] = reduce(lambda x,y: x+y, map(lambda x: x[DataProvider.NEvents], filelist))

		provider.saveState(workDir, "production.dbs", blocks)
	except:
		del mutex
		raise
	del mutex
	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))