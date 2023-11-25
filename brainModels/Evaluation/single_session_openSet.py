import logging
import os
from copy import deepcopy
from time import time
from typing import Optional, Union
import numpy as np
from mne.epochs import BaseEpochs
from sklearn.base import clone
from sklearn.metrics import get_scorer
from sklearn.model_selection import (
    GridSearchCV,
    LeaveOneGroupOut,
    StratifiedKFold,
    StratifiedShuffleSplit,
    RepeatedStratifiedKFold,
    GroupKFold,
    cross_val_score,
)
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from brainModels.Evaluation.base import BaseEvaluation
from sklearn import metrics
from sklearn.metrics import accuracy_score
import random
#from scipy.optimize import brentq
from scipy.interpolate import interp1d
from brainModels.Evaluation import score
from collections import OrderedDict
from sklearn.utils import shuffle
#from sklearn.mo
from sklearn.model_selection import (
    StratifiedKFold,
    StratifiedShuffleSplit,
    RepeatedStratifiedKFold,
    GroupKFold,
    cross_val_score,
    KFold
)
import mne
import tensorflow as tf
import pickle
import importlib
from brainModels.Evaluation.similarity import CalculateSimilarity

log = logging.getLogger(__name__)

Vector = Union[list, tuple, np.ndarray]

#########################################################################################################################################################
##########################################################################################################################################################
                                                    #Close-set Scenario
##########################################################################################################################################################
##########################################################################################################################################################

class SingleSessionCloseSet(BaseEvaluation):

    def __init__(
        self,
        n_perms: Optional[Union[int, Vector]] = None,
        data_size: Optional[dict] = None,
        # dataset=None,
        return_close_set=True,
        return_open_set=True,
        # paradigm=None,
        #paradigm=None,
        **kwargs
    ):
        # self.dataset = dataset
        # self.paradigm = paradigm
        #self.paradigm = paradigm
        self.n_perms = n_perms
        self.data_size = data_size
        self.return_close_set = return_close_set
        self.return_open_set = return_open_set
        super().__init__(**kwargs)

##########################################################################################################################################################
##########################################################################################################################################################
                                                #Single Session Evaluatiom for Siamese Network(Close-set Scenario)
##########################################################################################################################################################
##########################################################################################################################################################


    def _siamese_training(self, data, y, siamese, session):
        """Performing Ope-set lassification or in other terms EEG based Authentication"""
        groupfold = GroupKFold(n_splits=4)
        count_cv=0
        dicr3={}
        dicr2={}
        dicr1={}
        accuracy_list=[]
        auc_list=[]
        eer_list=[]
        eer_threshold_list=[]
        fpr_list=[]
        tpr_list=[]
        thresholds_list=[]
        fnr_list=[] 
        frr_1_far_list=[]
        mean_fpr = np.linspace(0, 1, 100)
        for train_index, test_index in groupfold.split(data, y, groups=y):
            x_train, x_test, y_train, y_test =data[train_index],data[test_index],y[train_index],y[test_index]
            scaler = StandardScaler()
            x_train = scaler.fit_transform(x_train.reshape((x_train.shape[0], -1))).reshape(x_train.shape)
            x_test = scaler.transform(x_test.reshape((x_test.shape[0], -1))).reshape(x_test.shape)

            tf.keras.backend.clear_session()
            model=siamese._siamese_embeddings(x_train.shape[1], x_train.shape[2])
            embedding_network=model
            #early_stopping_callback = EarlyStopping(monitor='val_loss', patience=10)
            train_dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(1000).batch(siamese.batch_size)
            history = embedding_network.fit(train_dataset,
                                        workers=siamese.workers,
                                        epochs=siamese.EPOCHS,
                                        verbose=siamese.verbose)

            resutls1,resutls2,resutls3=CalculateSimilarity._open_set_verification(model, x_test, y_test) 
            dicr1[count_cv] = resutls1
            dicr2[count_cv] = resutls2
            dicr3.update(dict(resutls3))
            count_cv=count_cv+1
        #average_scores=score._calculate_average_siamese_scores(tpr_list, eer_list, mean_fpr, auc_list, frr_1_far_list)
        return (dicr1, dicr2, dicr3)

    def deep_learning_method(self, dataset, pipelines):
        X, _, metadata=self.paradigm.get_data(dataset)
        results_saving_path=os.path.join(
            dataset.dataset_path,
            "Results",
            "SiameseWithinSessionEvaluation"
        )
        if not os.path.exists(results_saving_path):
            os.makedirs(results_saving_path)

        metadata=metadata[metadata['event_id']=="Deviant"]
        metadata=self._valid_subject_samples(metadata)
        target_index=metadata['event_id'].index.tolist()
        data=X[target_index]
        y=np.array(metadata["subject"])
        results_close_set=[]
        results_open_set=[]
        for session in np.unique(metadata.session):
            ix = metadata.session == session
            for name, clf in pipelines.items():
                siamese = clf[0]
                le = LabelEncoder()
                X_=data[ix]
                y_=y[ix]
                close_dicr1, close_dicr2, close_dicr3=self._siamese_training(X_, y_, siamese, session)
                close_set_path=os.path.join(results_saving_path,"close_set")
                if not os.path.exists(close_set_path):
                    os.makedirs(close_set_path)

                with open(os.path.join(close_set_path, "d1_dicr1.pkl"), 'wb') as f:
                    pickle.dump(close_dicr1, f)

                with open(os.path.join(close_set_path, "d1_dicr2.pkl"), 'wb') as f:
                    pickle.dump(close_dicr2, f)

                with open(os.path.join(close_set_path, "d1_dicr3.pkl"), 'wb') as f:
                    pickle.dump(close_dicr3, f)

                for sub in close_dicr3.keys():
                    result=close_dicr3[sub]
                    result=np.array(result)
                    true_lables=np.array(result[:,1])
                    predicted_scores=np.array(result[:,0])
                    inter_tpr, auc, eer, frr_1_far=score._calculate_siamese_scores(true_lables, predicted_scores)
                    res_close_set = {
                    'evaluation': 'Within Session',
                        "eval Type": "Close Set",
                        "dataset": dataset.code,
                        "pipeline": name,
                        "subject": sub,
                        "session": session,
                        "frr_1_far": frr_1_far,
                        #"accuracy": mean_accuracy,
                        "auc": auc,
                        "eer": eer,
                        "tpr": inter_tpr,
                        #"std_auc": std_auc,
                        "n_samples": len(X_)  # not training sample
                        #"n_channels": data.columns.size
                        }
                    results_close_set.append(res_close_set)


        return 0
    
##########################################################################################################################################################
##########################################################################################################################################################
                                        #Single Session Evaluatiom for State-of-the-algorithms(Close-set Scenario)
##########################################################################################################################################################
##########################################################################################################################################################
    

    def _authenticate_single_subject_open_set(self, imposters_data, imposters_labels, imposter_subject_ids, df_authenticated, pipeline):
            accuracy_list=[]
            auc_list=[]
            eer_list=[]
            eer_threshold_list=[]
            fpr_list=[]
            tpr_list=[]
            thresholds_list=[]
            fnr_list=[] 
            frr_1_far_list=[]
            #for name, clf in pipelines.items():
            mean_fpr = np.linspace(0, 1, 100)
            classifier=pipeline[-1]
            groupfold = GroupKFold(n_splits=4)
            for train_index, test_index in groupfold.split(imposters_data, imposters_labels, groups=imposter_subject_ids):
                X_train, X_test = imposters_data[train_index], imposters_data[test_index]
                y_train, y_test = imposters_labels[train_index], imposters_labels[test_index]
                imposter_train, imposter_test=imposter_subject_ids[train_index], imposter_subject_ids[test_index]


                # Assigning 75% samples of authenticated subject to training set
                num_rows = int(len(df_authenticated) * 0.75)
                df_authenticated_train=df_authenticated.sample(n=num_rows)

                # Assigning the remaining 25% samples of authenticated subject to testing set
                df_authenticated_test=df_authenticated.drop(df_authenticated_train.index)

                authenticated_train_lables=np.array(df_authenticated_train['Label'])
                authenticated_train_data=np.array(df_authenticated_train.drop(['Label','Event_id','Subject','session'],axis=1))

                authenticated_test_lables=np.array(df_authenticated_test['Label'])
                authenticated_test_data=np.array(df_authenticated_test.drop(['Label','Event_id','Subject','session'],axis=1))

                X_train = np.concatenate((X_train, authenticated_train_data))
                y_train = np.concatenate((y_train, authenticated_train_lables))
                X_test = np.concatenate((X_test, authenticated_test_data))
                y_test = np.concatenate((y_test, authenticated_test_lables))

                # Shuffle the training and testing data
                X_train, y_train = shuffle(X_train, y_train, random_state=42)
                X_test, y_test = shuffle(X_test, y_test, random_state=42)

                # Normalizing training and testing data using StandardScaler
                sc=StandardScaler()
                X_train=sc.fit_transform(X_train)
                X_test=sc.transform(X_test)
                clf=clone(classifier)
                
                # Training the model
                model=clf.fit(X_train,y_train)

                # Predicting the test set result
                y_pred=model.predict(X_test)
                y_pred_proba=model.predict_proba(X_test)[:,-1]

                # calculating auc, eer, eer_threshold, fpr, tpr, thresholds for each k-fold
                auc, eer, eer_theshold, inter_tpr, tpr, fnr, frr_1_far=score._calculate_scores(y_pred_proba,y_test, mean_fpr)
                accuracy_list.append(accuracy_score(y_test,y_pred))
                auc_list.append(auc)
                eer_list.append(eer)
                tpr_list.append(inter_tpr)
                fnr_list.append(fnr)
                frr_1_far_list.append(frr_1_far)
            average_scores=score._calculate_average_scores(accuracy_list, tpr_list, eer_list, mean_fpr, auc_list, frr_1_far_list)
            return average_scores
     
    def _open_set(self, df_session, pipeline, subject):

        #print("Geniune subject", subject)

        #print("Open set data size", len(df_session))
        df_authenticated=df_session[df_session['Subject']==subject]

        # getting the dataframe for rejected subjects
        df_imposters=df_session.drop(df_authenticated.index)

        # getting the subject IDs of the rejected subjects
        imposter_subject_ids = df_imposters.Subject.values

        imposters_labels=np.array(df_imposters['Label'])
        imposters_X=np.array(df_imposters.drop(['Label','Event_id','Subject','session'],axis=1))
        return self._authenticate_single_subject_open_set(imposters_X, imposters_labels, imposter_subject_ids, df_authenticated, pipeline)

    def _prepare_dataset(self, dataset, features):
        df_final=pd.DataFrame()
        for feat in range(0, len(features)-1):
            df=features[feat].get_data(dataset, self.paradigm)

            #print("length of features", len(df))
            #print("subject sample count", df['Subject'].value_counts())
            df_final = pd.concat([df_final, df], axis=1)

        if df_final.columns.duplicated().any():
            df_final = df_final.loc[:, ~df_final.columns.duplicated(keep='first')]

        subject_session_counts = df_final.groupby(['Subject', 'session']).size().reset_index(name='counts')

        # Identify subjects with sessions having fewer than 4 rows
        invalid_subject_sessions = subject_session_counts[subject_session_counts['counts'] < 4][['Subject', 'session']]
        
        # Filter out rows with invalid subject and session combinations
        df_final = df_final[~df_final.set_index(['Subject', 'session']).index.isin(invalid_subject_sessions.set_index(['Subject', 'session']).index)]
        #print(df_final[['session', 'Subject']].value_counts())

        #print(df[['session', 'Subject']].value_counts())

        return df_final
    
    def traditional_classification_methods(self, dataset, pipelines):
        results_close_set=[]
        results_open_set=[]
        #print("len of pipelines", pipelines.keys())
        for key, features in pipelines.items():
            print("features", features)
            data=self._prepare_dataset(dataset, features)
            #data=features[0].get_data(dataset, self.paradigm)
            for subject in tqdm(np.unique(data.Subject), desc=f"{key}-WithinSessionEvaluation"):
                df_subj=data.copy(deep=True)
                df_subj['Label']=0
                df_subj.loc[df_subj['Subject'] == subject, 'Label'] = 1
                #print("After Epochs rejection: ", len(df_subj))
                for session in np.unique(df_subj.session):
                    df_session= df_subj[df_subj.session==session]

                    if not self._valid_subject(df_session, subject, session):
                        continue

                    close_set_scores=self._close_set(df_session, pipelines[key])

                    mean_accuracy, mean_auc, mean_eer, mean_tpr, tprs_upper, tprr_lower, std_auc, mean_frr_1_far=close_set_scores
                    res_close_set = {
                    # "time": duration / 5.0,  # 5 fold CV
                    'evaluation': 'Within Session',
                    "eval Type": "Close Set",
                    "dataset": dataset.code,
                    "pipeline": key,
                    "subject": subject,
                    "session": session,
                    "frr_1_far": mean_frr_1_far,
                    "accuracy": mean_accuracy,
                    "auc": mean_auc,
                    "eer": mean_eer,
                    "tpr": mean_tpr,
                    "tprs_upper": tprs_upper,
                    "tprs_lower": tprr_lower,
                    "std_auc": std_auc,
                        "n_samples": len(df_subj)
                    #"n_samples": len(data)  # not training sample
                    #"n_channels": data.columns.size
                        }
                    results_close_set.append(res_close_set)
            


    def _evaluate(self, dataset, pipelines, algorithms_type):
        if algorithms_type=='DL':
            self.deep_learning_method(dataset, pipelines)

        else:
            self.traditional_classification_methods(dataset, pipelines)

            

        # else:
        #     self.


        # results_close_set=[]
        # results_open_set=[]
        # eeg_data_dict=dataset.get_data()
        # # Extract the data and labels from the dictionary
        # data = []
        # labels = []

        # for subject_id, sessions in eeg_data_dict.items():
        #     for session_id, runs in sessions.items():
        #         for run_id, raw_data in runs.items():
        #         # Assuming 'raw_data' contains your EEG data
        #             print("Subject", subject_id, raw_data.get_data().shape)
        #             data.append(raw_data)
        #             labels.append(subject_id)  # Use subject ID as a label

        # d=mne.concatenate_raws(data, preload=True, verbose=False)
        # print("raw data shape", d.get_data().shape)

        return 0
   
    
    def evaluate(self, dataset, pipelines, algorithms_type):
        results, scenario=self._evaluate(dataset, pipelines, algorithms_type)
        results_path=os.path.join(
            dataset.dataset_path,
            "Results",
            "SingleSessionEvaluation"
        )
        return results, results_path, scenario
    
    def _valid_subject(self, df, subject, session):
        """Checks if the dataframe has 4 subjects since open set requires at least 4 subjects because of group k fold with k=4"""

        no_of_subjects=len(df['Subject'].unique())
        if no_of_subjects<4:
            return False  
        else:
            return True
    
    def is_valid(self, dataset):
        return True



    