import logging
import os
from copy import deepcopy
from time import time
from typing import Optional, Union
import joblib
import numpy as np
from mne.epochs import BaseEpochs
from sklearn.base import clone
from sklearn.metrics import get_scorer
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    GroupKFold,
    LeaveOneGroupOut
    ,
)
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler
from deeb.Evaluation.base import BaseEvaluation
#from deeb.evaluation.scores import Scores as score
from collections import OrderedDict
import tensorflow as tf
from sklearn.metrics.pairwise import cosine_similarity as cs
from collections import defaultdict
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from deeb.pipelines.siamese import Siamese
from keras.callbacks import EarlyStopping
from collections import defaultdict
from deeb.Evaluation.scores import Scores as score
import pickle
import mne
from tabnanny import verbose
from tqdm import tqdm 
log = logging.getLogger(__name__)

Vector = Union[list, tuple, np.ndarray]

# This function has been sourced from https://git.scc.kit.edu/ps-chair/brainnet licensed under the Creative Commons
def _predict_open_set(embedding_network, x_test, y_test):
    """Calculates similarity values for authentication (verification) by 
    comparing each face embedding in the test set with all other face embeddings, and then calculating the cosine similarity between 
    each pair of embeddings. It then uses these similarity values to create pairs of faces, with the label 1 indicating that the faces
    belong to the same individual and label 0 indicating that the faces belong to different individuals."""

    print("I am in predict open set function")
    # Compute embeddings for all test samples
    resutls=[]
    resutls2=[]
    resutls3=defaultdict(list)
    pair1=[]
    pair2=[]
    calss=np.unique(y_test)
    TP,FP,TN,FN=0,0,0,0
    digit_indices = [np.where(y_test == i)[0] for i in np.unique(y_test)]
    x_test_1 = x_test
    print(len(x_test))
    #anc_et=embedding_network(x_train_val)
    anc_e=embedding_network(x_test[0:min(500,len(x_test))])
    for c in tqdm(range(len(x_test)//500), desc='Getting test embedings'):
        anc_e=tf.concat(axis=0, values = [anc_e, embedding_network(x_test[(c+1)*500:min((c+2)*500,len(x_test))])]) 	
    print(len(x_test))
    for i in tqdm(range(len(x_test_1)), desc="Calculating similarity"):
        temp=np.where(calss == y_test[i])[0][0]
        prediction=[]
        same_in=digit_indices[np.where(calss == y_test[i])[0][0]]
        for t in range(len(x_test_1)):
            tempp=-1*euclidean_distance2(anc_e[t],anc_e[i]).numpy()[0]
    
            if t in same_in:
                if t==i:
                    pass
                else:
                    resutls.append([tempp,1,y_test[i],y_test[t]])
            else:
                resutls.append([tempp,0,y_test[i],y_test[t]])    
            prediction.append(tempp)
        prediction=np.array(prediction)
        
        for j in calss:
            same_in=digit_indices[np.where(calss == j)[0][0]]
            same_in=np.setdiff1d(same_in,[i])
            spredict=max(prediction[same_in])        
    
            if y_test[i] ==j:
                resutls2.append([spredict,1,y_test[i],j])
                resutls3[j].append([spredict,1,y_test[i],j])
            else:
                resutls2.append([spredict,0,y_test[i],j])
                resutls3[j].append([spredict,0,y_test[i],j])
                    
            if spredict>0.85:
                if y_test[i] ==j:
                    TP+=1
                else:
                    FP+=1
            else:
                if y_test[i] == j:
                    FN+=1
                else:
                    TN+=1
    return resutls,resutls2,resutls3

# This function has been sourced from https://git.scc.kit.edu/ps-chair/brainnet licensed under the Creative Commons
def _predict_close_set(embedding_network, x_train_val, y_train_val, x_test, y_test):
    """Calculates similarity values for closed-set recognition by comparing each face embedding in the test set with all face embeddings 
    in the training set, and then calculating the cosine similarity between each pair of embeddings. It then uses these similarity 
    values to create pairs of faces, with the label 1 indicating that the faces belong to the same individual (from the training set) 
    and label 0 indicating that the faces belong to different individuals (including unknown identities)"""

    print("I am in predict close set function")
    resutls=[]
    resutls2=[]
    resutls3=defaultdict(list)
    #pair1=[]
    #pair2=[]
    #calss=np.unique(y_test)
    calsstrain=np.unique(y_train_val)
    TP,FP,TN,FN=0,0,0,0
    #print("avinash")
    #print("y Train", y_train_val)
    #print("size of y Train", len(y_train_val))
    digit_indices = [np.where(y_train_val == i)[0] for i in np.unique(y_train_val)]
    #print("chaurasia")
    x_test_1 = x_test

    print(len(x_train_val),len(x_test))
    #anc_et=embedding_network(x_train_val)
    anc_e=embedding_network(x_test[0:min(500,len(x_test))])
    for c in range(len(x_test)//500):
        anc_e=tf.concat(axis=0, values = [anc_e, embedding_network(x_test[(c+1)*500:min((c+2)*500,len(x_test))])]) 	
    anc_et=embedding_network(x_train_val[0:min(500,len(x_train_val))])
    for c in range(len(x_train_val)//500):
        anc_et=tf.concat(axis=0, values = [anc_et, embedding_network(x_train_val[(c+1)*500:min((c+2)*500,len(x_train_val))])]) 
    #print(type(anc_e))
    print(len(anc_et),len(anc_e))
    for i in tqdm(range(len(x_test_1)), desc="Calculating similarity"):
        prediction=[]
        test_e=embedding_network(np.array([x_test[i]]))
        same_in=digit_indices[np.where(calsstrain == y_train_val[i])[0][0]]
        
        for t in range(len(x_train_val)):
            tempp=-1*euclidean_distance2(anc_et[t],test_e).numpy()[0][0] 
            if y_test[i] ==y_train_val[t]:
                resutls.append([tempp,1,y_test[i],y_train_val[t]])
            else:
                resutls.append([tempp,0,y_test[i],y_train_val[t]])

            prediction.append(tempp)        
        prediction=np.array(prediction)
        
        for j in calsstrain:
            same_in=digit_indices[np.where(calsstrain == j)[0][0]]
            spredict=((sum(prediction[same_in]))/(len(same_in)))            
            if y_test[i] ==j:
                resutls2.append([spredict,1,y_test[i],j])
                resutls3[j].append([spredict,1,y_test[i],j])
            else:
                resutls2.append([spredict,0,y_test[i],j])
                resutls3[j].append([spredict,0,y_test[i],j])   
            if spredict>0.85:
                if y_test[i] ==j:
                    TP+=1
                else:
                    FP+=1
            else:
                if y_test[i] == j:
                    FN+=1
                else:
                    TN+=1
    return resutls,resutls2,resutls3
            
def euclidean_distance2(x, y):
	sum_square = tf.math.reduce_sum(tf.math.square(x - y), axis=None, keepdims=True)
	return tf.math.sqrt(tf.math.maximum(sum_square, tf.keras.backend.epsilon()))

# def _normalize_train(X, sc):
#     X_fin = []
#     for i in np.arange(X.shape[0]):
#         X_p = sc.fit_transform(X[i])
#         X_fin.append(X_p)
#     X_fin = np.array(X_fin)

#     return X_fin

# def _normalize_test(X, sc):
#     X_fin = []
#     for i in np.arange(X.shape[0]):
#         X_p = sc.transform(X[i])
#         X_fin.append(X_p)
#     X_fin = np.array(X_fin)

#     return X_fin


class Siamese_WithinSessionEvaluation(BaseEvaluation):
    def __init__(
        self,
        n_perms: Optional[Union[int, Vector]] = None,
        data_size: Optional[dict] = None,
        # dataset=None,
        return_close_set: bool = True,
        return_open_set: bool = True,
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
    
    def _close_set(self, data, y, siamese, session):
        
        #print("Close Set")
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
        skfold = StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
        #print("skfold", skold)
        for train_index, test_index in skfold.split(data, y):
            x_train, x_test, y_train, y_test =data[train_index],data[test_index],y[train_index],y[test_index]

            # Normalizing the training and test data
            #sc=StandardScaler()
            # x_train=sc.fit_transform(x_train)
            # x_test=sc.transform(x_test)

            #X_train=_normalize_train(x_train, sc)
            #X_test=_normalize_test(x_test, sc)

            tf.keras.backend.clear_session()
            model=siamese._siamese_embeddings(x_train.shape[1], x_train.shape[2])
            embedding_network=model
            early_stopping_callback = EarlyStopping(monitor='val_loss', patience=10)
            train_dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(1000).batch(siamese.batch_size)
            history = embedding_network.fit(train_dataset,
                                        workers=siamese.workers,
                                        epochs=siamese.EPOCHS,
                                        verbose=siamese.verbose)
            resutls1,resutls2,resutls3=_predict_close_set(model, x_train, y_train, x_test, y_test) 
            resutls=np.array(resutls2)
            true_lables=resutls[:,1]
            predicted_lables=resutls[:,0]
            inter_tpr, auc, eer, frr_1_far=score._calculate_siamese_scores(predicted_lables, true_lables, mean_fpr)
            auc_list.append(auc)
            eer_list.append(eer)
            tpr_list.append(inter_tpr)
            frr_1_far_list.append(frr_1_far)

            dicr1[count_cv] = resutls1
            dicr2[count_cv] = resutls2
            dicr3.update(dict(resutls3))
            count_cv=count_cv+1
        average_scores=score._calculate_average_siamese_scores(tpr_list, eer_list, mean_fpr, auc_list, frr_1_far_list)
        return (average_scores, dicr1, dicr2, dicr3)

        
        # close_set_path=os.path.join(results_path,"close_set")
        # if not os.path.exists(close_set_path):
        #     os.makedirs(close_set_path)
        # with open(os.path.join(close_set_path, "d1_dicr1.pkl"), 'wb') as f:
        #     pickle.dump(dicr1, f)

        # with open(os.path.join(close_set_path, "d1_dicr2.pkl"), 'wb') as f:
        #     pickle.dump(dicr2, f)

        # with open(os.path.join(close_set_path, "d1_dicr3.pkl"), 'wb') as f:
        #     pickle.dump(dicr3, f)

        # return (dicr1, dicr2, dicr3)
    
    def _open_set(self, data, y, siamese, session):
        """Performing Ope-set lassification or in other terms EEG based Authentication"""
        groupfold = GroupKFold(n_splits=5)
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

        # print("X shape", data.shape)
        # print("y shape", y.shape)
        for train_index, test_index in groupfold.split(data, y, groups=y):
            # X_train, X_test = data[train_index], data[test_index]
            # y_train, y_test = y[train_index], y[test_index]
            #x_test = x_test.astype("float32")
            # print("X_train", X_train.shape)
            # print("X_test", X_test.shape)
            # print("y_train", np.unique(y_train))
            # print("y_test", np.unique(y_test))
            x_train, x_test, y_train, y_test =data[train_index],data[test_index],y[train_index],y[test_index]

            # # Normalizing the training and test data
            #sc=StandardScaler()
            # x_train=sc.fit_transform(x_train)
            # x_test=sc.transform(x_test)

            # X_train=_normalize_train(x_train, sc)
            # X_test=_normalize_test(x_test, sc)

            tf.keras.backend.clear_session()
            model=siamese._siamese_embeddings(x_train.shape[1], x_train.shape[2])
            embedding_network=model
            early_stopping_callback = EarlyStopping(monitor='val_loss', patience=10)
            train_dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(1000).batch(siamese.batch_size)
            history = embedding_network.fit(train_dataset,
                                        workers=siamese.workers,
                                        epochs=siamese.EPOCHS,
                                        verbose=siamese.verbose)

            resutls1,resutls2,resutls3=_predict_open_set(model, x_test, y_test) 
            resutls=np.array(resutls2)
            true_lables=resutls[:,1]
            predicted_lables=resutls[:,0]
            inter_tpr, auc, eer, frr_1_far=score._calculate_siamese_scores(predicted_lables, true_lables, mean_fpr)
            auc_list.append(auc)
            eer_list.append(eer)
            tpr_list.append(inter_tpr)
            frr_1_far_list.append(frr_1_far)

            dicr1[count_cv] = resutls1
            dicr2[count_cv] = resutls2
            dicr3.update(dict(resutls3))
            count_cv=count_cv+1
        average_scores=score._calculate_average_siamese_scores(tpr_list, eer_list, mean_fpr, auc_list, frr_1_far_list)
        return (average_scores, dicr1, dicr2, dicr3)
        

        # open_set_path=os.path.join(results_path,"open_set")
        # if not os.path.exists(open_set_path):
        #     os.makedirs(open_set_path)
        # with open(os.path.join(open_set_path, "d1_dicr1.pkl"), 'wb') as f:
        #     pickle.dump(dicr1, f)

        # with open(os.path.join(open_set_path, "d1_dicr2.pkl"), 'wb') as f:
        #     pickle.dump(dicr2, f)

        # with open(os.path.join(open_set_path, "d1_dicr3.pkl"), 'wb') as f:
        #     pickle.dump(dicr3, f)

        # return (dicr1, dicr2, dicr3)
    
    # def _prepare_dataset(self):
    #     epochs_dir="/scratch/hpc-prf-bbam/avinashk/mne_data/MNE-erpcoren400-data/v1/resources/29xpq/providers/osfstorage/Epochs"
    #     epochs_list=[]
    #     for i in range(1,41):
    #         subject_dir=" "
    #         session_dir=" "
    #         subject_dir=os.path.join(epochs_dir, str(i))
    #         session_dir=os.path.join(subject_dir, "session_1")
    #         epochs=mne.read_epochs(os.path.join(session_dir, "run_1_epochs.fif"), preload=True, verbose=False)
    #         epochs=epochs['Inconsistent']
    #         epochs_list.append(epochs)
    #     X=mne.concatenate_epochs(epochs_list)
    #     X=X.get_data()	

    #     subject=1
    #     Y=[]
    #     for epochs in epochs_list:
    #         count = epochs.get_data().shape[0]
    #         subject_ids = np.full((count,), subject)
    #         Y.append(subject_ids)
    #         subject += 1

    #     Y = np.concatenate(Y)	
    #     return X, Y
        
 
    def _evaluate(self, dataset, pipelines):        
        y=[]
        X, _, metadata=self.paradigm.get_data(dataset)
        
        #print("Number of Target samples", metadata['event_id'].value_counts())

        metadata=self._valid_subject_samples(metadata)
        if(dataset.paradigm == "p300"):
            target_index=metadata[metadata['event_id']=="Target"].index.tolist()
            metadata=metadata[metadata['event_id']=="Target"]

        elif (dataset.paradigm == "n400"):
            target_index=metadata[metadata['event_id']=="Inconsistent"].index.tolist()
            metadata=metadata[metadata['event_id']=="Inconsistent"]
        
        # Selecting the target trials if paradigm is p300 or inconsistent if paradigm is n400
        data=X[target_index]

        # Selecting the subject labels for the target or inconsistent trails
        #y=metadata.iloc[target_index]["subject"].tolist()
        y=np.array(metadata["subject"])
        #print("Y: ", type(y), y)
        # iterate over sessions
        results_close_set=[]
        results_open_set=[]
        #X_data, y_data=self._prepare_dataset()
        # Check if X and X_data are equal

        #X_matin=np.load('/scratch/hpc-prf-bbam/avinashk/brainnet/Data/D_2_X.npy')
        #y_matin=np.load('/scratch/hpc-prf-bbam/avinashk/brainnet/Data/D_2_Y.npy')


        for session in np.unique(metadata.session):
            ix = metadata.session == session
            for name, clf in pipelines.items():
                siamese = clf[0]
                le = LabelEncoder()
                X_=data[ix]
                y_=y[ix]
                #print("shape pf y", y_)
                # print("Later checking x and x_data", np.array_equal(X_, X_data))
                # print("Later checking y and y_data",np.array_equal(y_, y_data))

                if self.return_close_set:
                    average_scores, dicr1, dicr2, dicr3=self._close_set(X_, y_, siamese, session)
                    mean_auc, mean_eer, mean_tpr, tprs_upper, tprr_lower, std_auc, mean_frr_1_far=average_scores
                    res_close_set = {
                       # "time": duration / 5.0,  # 5 fold CV
                       'evaluation': 'Siamese Within Session',
                        "eval Type": "Close Set",
                        "dataset": dataset.code,
                        "pipeline": name,
                        #"subject": subject,
                        "session": session,
                        "frr_1_far": mean_frr_1_far,
                        #"accuracy": mean_accuracy,
                        "auc": mean_auc,
                        "eer": mean_eer,
                        "tpr": mean_tpr,
                        "tprs_upper": tprs_upper,
                        "tprs_lower": tprr_lower,
                        "std_auc": std_auc,
                        #"n_samples": len(data)  # not training sample
                        #"n_channels": data.columns.size
                         }
                    results_close_set.append(res_close_set)

                if self.return_open_set:
                    average_scores, dicr1, dicr2, dicr3=self._open_set(X_, y_, siamese, session)  
                    mean_auc, mean_eer, mean_tpr, tprs_upper, tprr_lower, std_auc, mean_frr_1_far=average_scores 
                    res_open_set = {
                       # "time": duration / 5.0,  # 5 fold CV
                       'evaluation': 'Siamese Within Session',
                        "eval Type": "Open Set",
                        "dataset": dataset.code,
                        "pipeline": name,
                        #"subject": subject,
                        "session": session,
                        "frr_1_far": mean_frr_1_far,
                       # "accuracy": mean_accuracy,
                        "auc": mean_auc,
                        "eer": mean_eer,
                        "tpr": mean_tpr,
                        "tprs_upper": tprs_upper,
                        "tprs_lower": tprr_lower,
                        "std_auc": std_auc,
                        #"n_samples": len(data)  # not training sample
                        #"n_channels": data.columns.size
                        }
                    results_open_set.append(res_open_set)  

        if self.return_close_set ==True and self.return_open_set== False:
            scenario='close_set'
            return results_close_set, scenario

        if self.return_close_set ==False and self.return_open_set== True:
            scenario='open_set'
            return results_open_set, scenario
        
        if self.return_close_set ==True and self.return_open_set== True:
            scenario=['close_set', 'open_set']
            return (results_close_set, results_open_set), scenario
        
    def evaluate(self, dataset, pipelines, param_grid):
        results, scenario=self._evaluate(dataset, pipelines)

        results_path=os.path.join(
            dataset.dataset_path,
            "Results",
            "SiameseWithinSessionEvaluation"
            #f"{dataset.code}_CloseSetEvaluation")
        )
        if not os.path.exists(results_path):
            os.makedirs(results_path)
        #print(type(results))
        return results, results_path, scenario
    
    def _valid_subject_samples(self, metadata):
        subject_session_counts = metadata.groupby(['subject', 'session']).size().reset_index(name='counts')

        # Identify subjects with sessions having fewer than 4 rows
        invalid_subject_sessions = subject_session_counts[subject_session_counts['counts'] < 8][['subject', 'session']]
        
        # Filter out rows with invalid subject and session combinations
        metadata = metadata[~metadata.set_index(['subject', 'session']).index.isin(invalid_subject_sessions.set_index(['subject', 'session']).index)]
        return metadata
 
    def is_valid(self, dataset):
        return True
    
# This needs to be checked later and modified
class Siamese_CrossSessionEvaluation(BaseEvaluation):
    def __init__(
        self,
        n_perms: Optional[Union[int, Vector]] = None,
        data_size: Optional[dict] = None,
        # dataset=None,
        return_close_set: bool = True,
        return_open_set: bool = True,
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
    
    def _close_set(self, data, y, grid_clf, groups=None):
        average_session_results=[]
        cv=LeaveOneGroupOut()
        for train, test in cv.split(data, y, groups):
            X_train, X_test, y_train, y_test = data[train], data[test], y[train], y[test]
            tf.keras.backend.clear_session()
            train_dataset = tf.data.Dataset.from_tensor_slices((X_train, y_train)).shuffle(1000).batch(128)
            model=grid_clf._siamese_embeddings(X_train.shape[1], X_train.shape[2])
            early_stopping_callback = EarlyStopping(monitor='val_loss', patience=10)
            history = model.fit(train_dataset,
                                        workers=5,
                                        callbacks=[early_stopping_callback])
            results=self._predict(model, X_test, y_test) 
            average_session_results.append(results) 
         
        return average_session_results
    
    def _open_set(self, X, y, grid_clf, groups=None):
        average_session_results=[]
        cv = LeaveOneGroupOut()
        for train_index, test_index in cv.split(X, y, groups=groups):
            X_train, X_test = [train_index], X[test_index]
            y_train, y_test = y[train_index], y[test_index]

            # Get the unique subject_ids from y_train
            train_subject_ids = np.unique(y_train)

            # Randomize the subject_ids
            np.random.shuffle(train_subject_ids)

            # Select 75% of the subject_ids to be used for training
            train_subject_ids = train_subject_ids[:int(0.75 * len(train_subject_ids))]

            # remove the subject_ids from y_test that are present in train_subject_ids
            test_subject_ids = np.unique(y_test)
            test_subject_ids = [subject_id for subject_id in test_subject_ids if subject_id not in train_subject_ids]

            # Select the samples from X_test and y_test that correspond to the test_subject_ids
            X_test = X_test[np.isin(y_test, test_subject_ids)]
            y_test = y_test[np.isin(y_test, test_subject_ids)]

            # Select the samples from X_train and y_train that correspond to the train_subject_ids
            X_train = X_train[np.isin(y_train, train_subject_ids)]
            y_train = y_train[np.isin(y_train, train_subject_ids)]
            tf.keras.backend.clear_session()
            train_dataset = tf.data.Dataset.from_tensor_slices((X_train, y_train)).shuffle(1000).batch(128)
            model=grid_clf._siamese_embeddings(X_train.shape[1], X_train.shape[2])
            early_stopping_callback = EarlyStopping(monitor='val_loss', patience=10)
            history = model.fit(train_dataset,
                                        workers=5,
                                        callbacks=[early_stopping_callback])
            results=self._predict(model, X_test, y_test) 
            average_session_results.append(results) 
         
        return average_session_results
        
        #return average_session_results 
    def _evaluate(self, dataset, pipelines):
        if not self.is_valid(dataset):
            raise AssertionError("Dataset is not appropriate for evaluation")

        #y=[]
        results_close_set=[]
        results_open_set=[]
        X, _, metadata=self.paradigm.get_data(dataset)
        if(dataset.paradigm == "p300"):
            target_index=metadata[metadata['event_id']=="Target"].index.tolist()
            metadata=metadata[metadata['event_id']=="Target"]

        elif (dataset.paradigm == "n400"):
            target_index=metadata[metadata['event_id']=="Inconsistent"].index.tolist()
            metadata=metadata[metadata['event_id']=="Inconsistent"]
        
        # Selecting the target trials if paradigm is p300 or inconsistent if paradigm is n400
        data=X[target_index]

        # Selecting the subject labels for the target or inconsistent trails
        #y=metadata.iloc[target_index]["subject"].tolist()
        y=np.array(metadata["subject"])

        # iterate over sessions
        # for session in np.unique(metadata.session):
        #     ix = metadata.session == session

        groups = metadata.session.values
        for name, clf in pipelines.items():
            
            grid_clf = clone(clf)
            if self.return_close_set:
                close_set_scores=self._close_set(data, y, grid_clf, groups=groups)
                mean_accuracy, mean_auc, mean_eer, mean_tpr, tprs_upper, tprr_lower, std_auc, mean_frr_1_far=close_set_scores
                
            if self.return_open_set:
                open_set_scores=self._open_set(data, y, grid_clf, groups=groups) 
                mean_accuracy, mean_auc, mean_eer, mean_tpr, tprs_upper, tprr_lower, std_auc, mean_frr_1_far=open_set_scores
         
        return 0
    
    def is_valid(self, dataset):
        return dataset.n_sessions > 1

    