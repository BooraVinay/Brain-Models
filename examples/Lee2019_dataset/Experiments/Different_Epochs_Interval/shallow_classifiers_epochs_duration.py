import sys
sys.path.append('/scratch/hpc-prf-bbam/avinashk/Brain-Models/')
import abc
import logging
import mne
import numpy as np
import pandas as pd
from brainModels.preprocessing.erp import ERP
from brainModels.datasets.brainInvaders15a import BrainInvaders2015a
from brainModels.datasets.mantegna2019 import Mantegna2019
from brainModels.datasets.cogBciFlanker import COGBCIFLANKER
from brainModels.datasets.lee2019 import Lee2019
#from brainmodels.datasets.draschkow2018 import Draschkow2018
from brainModels.datasets.won2022 import Won2022
from brainModels.featureExtraction.features import AutoRegressive 
from brainModels.featureExtraction.features import PowerSpectralDensity 
#from deeb.pipelines.siamese_old import Siamese
from brainModels.featureExtraction.base import Basepipeline
#from deeb.evaluation.evaluation import CloseSetEvaluation, OpenSetEvaluation
from brainModels.datasets import utils
from autoreject import AutoReject, get_rejection_threshold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler 
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from brainModels.evaluations.single_session_close_set import SingleSessionCloseSet
from brainModels.evaluations.single_session_open_set import SingleSessionOpenSet
#from brainModels.evaluations.multi_session_open_set_copy import MultiSessionOpenSet
from brainModels.featureExtraction.siamese import Siamese
from brainModels.datasets.lee2019 import Lee2019
import os

def _evaluate():

    duration_list=[]
    for interval in [0.8, 1, 1.2, 1.4, 1.6, 1.8]:
    #for interval in [0.8]:
        data=Lee2019()
        data.interval=[-0.2, interval]
        paradigm_n400=ERP()

        pipeline={}
        pipeline['AR+PSD+SVM']=make_pipeline(AutoRegressive(order=1), PowerSpectralDensity(), SVC(kernel='rbf', class_weight="balanced", probability=True))
        pipeline['AR+PSD+LR']=make_pipeline(AutoRegressive(order=1),PowerSpectralDensity(), LogisticRegression(class_weight="balanced"))
        # #pipeline['PSD+LR']=make_pipeline(AutoRegressive(order=6), PowerSpectralDensity(), LogisticRegression())
        pipeline['AR+PSD+LDA']=make_pipeline(AutoRegressive(order=1),PowerSpectralDensity(), LDA(solver='lsqr', shrinkage='auto'))
        #pipeline['siamese']=make_pipeline(Siamese(user_siamese_path='/scratch/hpc-prf-bbam/avinashk/mne_data/User_method/siamese_method.py'))
        # #pipeline['PSD+LDA']=make_pipeline(AutoRegressive(order=6), PowerSpectralDensity(), LDA(solver='lsqr', shrinkage='auto'))
        pipeline['AR+PSD+NB']=make_pipeline(AutoRegressive(order=1),PowerSpectralDensity(), GaussianNB())
        # #pipeline['PSD+NB']=make_pipeline(AutoRegressive(order=6), PowerSpectralDensity(), GaussianNB())
        pipeline['AR+PSD+KNN']=make_pipeline(AutoRegressive(order=1),PowerSpectralDensity(), KNeighborsClassifier())
        # #pipeline['PSD+KNN']=make_pipeline(AutoRegressive(order=6), PowerSpectralDensity(), KNeighborsClassifier(n_neighbors=3))
        pipeline['AR+PSD+RF']=make_pipeline(AutoRegressive(order=1),PowerSpectralDensity(), RandomForestClassifier(class_weight="balanced"))
        open_set=SingleSessionOpenSet(paradigm=paradigm_n400, datasets=data, overwrite=False)
        results=open_set.process(pipeline)

        duration=interval+0.2
        results['epochs_duration']=duration
        duration_list.append(results)

    df=pd.concat(duration_list, axis=0)
    curent_dir=os.getcwd()
    fname='epochs_duration_shallow_classifiers_results.csv'
    results_directory=os.path.join(curent_dir, "Shallow_Classifiers_Results", fname)
    df.to_csv(fname)

if __name__ == '__main__':
    result= _evaluate()
    