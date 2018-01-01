#!/usr/local/bin/python
#######################################################
#            File description
#######################################################
#  Run a series of CFD++ cases to obtain CL-Alpha property
#
#######################################################
#    Date        Author        Comment
#  01-Jan-2018   Jiamin Xu     Initial creation
#######################################################
#            Import module
#######################################################
import os
import re
import math
import shutil

#######################################################
#            Constants
#######################################################


#######################################################
#            Class
#######################################################
class CFDppWrapper:
    def __init__(self, caseName, fromCaseName, ntstep):
        '''Initialize function'''
        self.caseName = caseName                  ## name of current case
        self.fromCaseName = fromCaseName          ## name of restart case
        self.logFileName = caseName + ".log"

        self.numProcs = -1
        self.ntStep = ntstep

        self.velx = 0.0
        self.vely = 0.0
        self.velz = 0.0

        self.prefix = "===" + self.caseName + "=== "

    def Validate(self):
        status = True
        
        ## Check number of processors
        if self.numProcs <= 0:
            print (self.prefix + "Wrong processor number!!!")
            return False

        return status


    def CreateCasedir(self):
        '''Copy/Create CFD++ input files'''
        try:
            print (self.prefix + "Creating input files for " + self.caseName + " based on " + self.fromCaseName + "...")
            sourceDir = "./" + self.fromCaseName
            targetDir = "./" + self.caseName
            numCopiedFiles = 0
            filesToCopy = ["nodesin.bin",                            ## basic input
                           "mcfd.bc",                                ## basic input
                           "exbcsin.bin",                            ## basic input
                           "cellsin.bin",                            ## basic input
                           "npfopts.inp",                            ## basic output settings
                           "mcfd_metis.graph",                       ## mpi input
                           "mcpusin.bin."+str(self.numProcs),        ## mpi input
                           "mcfd.inp",                               ## cfd++ main control input
                           "cdepsout.bin",                           ## restart input
                           "infout1f.inp"]                           ## reference values

            if not os.path.exists(sourceDir):
                return False

            ## create case folder if not exists
            if not os.path.exists(targetDir):
                os.makedirs(targetDir)
            else:
                shutil.rmtree(targetDir)
                os.makedirs(targetDir)
            
            for sourceFile in os.listdir(sourceDir):
                if sourceFile in filesToCopy:
                    sourceFilePath = os.path.join(sourceDir, sourceFile)
                    targetFilePath = os.path.join(targetDir, sourceFile)            
                    shutil.copyfile(sourceFilePath, targetFilePath)
                    numCopiedFiles += 1

            if numCopiedFiles < 10:
                return False
        except Exception,e:
            print e
            exit(1)
        else:
            print self.prefix + str(numCopiedFiles) + " copied into " + self.caseName + "!"
            return True

        
    def RunCFDpp(self):
        '''Execute current CFD++ case'''
        runCFDpp = "mpiexec -n " + str(self.numProcs) + " mpimcfd > " + self.logFileName
        try:
            ret = os.chdir(self.caseName)
            print self.prefix + runCFDpp
            ret = os.system(runCFDpp)
            ret = os.chdir("..")
        except Exception,e:
            print e
            exit(1)
        else:
            print self.prefix + "Computation finished!!!"


class ClAlphaDriver(CFDppWrapper):
    def __init__(self, caseName, fromCaseName, ntstep, alpha):
        CFDppWrapper.__init__(self, caseName, fromCaseName, ntstep)
        
        self.alpha = alpha  ## angle of attack
        self.isRestart = True

        pass

    
    def CreateInpFile(self):
        '''Create mcfd.inp file for current case'''
        try:
            inpFile = open("./" + self.caseName + "/mcfd.inp")
            inpTexts = inpFile.readlines()

            for i in range(len(inpTexts)):
                ## check "istart"
                if "istart" in inpTexts[i]:
                    inpTexts[i] = "istart " + str(int(self.isRestart)) + "\n"

                ## check "ntstep"
                if "ntstep" in inpTexts[i]:
                    inpTexts[i] = "ntstep " + str(self.ntStep) + "\n"

                ## check primitive variables
                if "#vals 6 title primitive_variables_2" in inpTexts[i]]:
                    line = inpTexts[i+1]
                    pres = float(line.split()[1])
                    temp = float(line.split()[2])
                    velx = float(line.split()[3])
                    vely = float(line.split()[4])
                    velz = float(line.split()[5])
                    velm = math.sqrt(velx*velx + vely*vely + velz*velz)
                    sinA = math.sin(math.radians(self.alpha))
                    cosA = math.cos(math.radians(self.alpha))

                    self.velx = velm*cosA
                    self.velz = velm*sinA
                    priVarText = "values " + str(pres) + " " + str(temp) + " " + \
                                 str(self.velx) + " " + str(self.vely) + " " + str(self.velz) + "\n"
                    inpTexts[i+1] = priVarText

                ## check aero inputs
                if "aero_u" in inpTexts[i]:
                    inpTexts[i] = "aero_u " + str(self.velx) + "\n"

                if "aero_v" in inpTexts[i]:
                    inpTexts[i] = "aero_v " + str(self.vely) + "\n"

                if "aero_w" in inpTexts[i]:
                    inpTexts[i] = "aero_w " + str(self.velz) + "\n"

                if "aero_alpha" in inpTexts[i]:
                    inpTexts[i] = "aero_alpha " + str(self.alpha) + "\n"

                if "cldriver " in inpTexts[i]:
                    inpTexts[i] = "cldriver 0\n"
  
            ## write new mcfd.inp file
            newInpFile = open("./" + self.caseName + "/mcfd.inp",'wb')
            for i in range(len(inpTexts)):
                if inpTexts[i].strip():
                    newInpFile.write(inpTexts[i])
            newInpFile.close()

            refInpFile = open("./" + self.caseName + "/infout1f.inp")
            refInpTexts = refInpFile.readlines()

            for i in range(len(refInpTexts)):
                if "alpha" in refInpTexts[i]:
                    refInpTexts[i] = "alpha " + str(self.alpha) + "\n"
           
            ## write new infout1f.inp file
            newRefInpFile = open("./" + self.caseName + "/infout1f.inp",'wb')
            for i in range(len(refInpTexts)):
                newRefInpFile.write(refInpTexts[i])
            newRefInpFile.close()

        except Exception,e:
            print e
            exit(1)    
        
            
                
#######################################################
#            Main Function
#######################################################
if __name__ == '__main__':


