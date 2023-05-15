import sys
sys.path.append('/Users/avinashkumarchaurasia/Master_Thesis/deeb/deeb')
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC
# from deeb.paradigms.erp import P300
# from deeb.paradigms.erp import N400
from deeb.paradigms.p300 import P300
from deeb.paradigms.n400 import N400
from deeb.pipelines.utils import (
    parse_pipelines_from_directory,
    generate_paradigms,
    parse_pipelines_for_single_dataset,
    get_paradigm_from_config,)
import os
from collections import OrderedDict
from copy import deepcopy
from sklearn.base import BaseEstimator, TransformerMixin
from glob import glob
import importlib
import logging
import os.path as osp
from pathlib import Path
import mne
import numpy as np
import yaml
import pandas as pd
from deeb.datasets import (BrainInvaders2015a, Mantegna2019, ERPCOREN400, Lee2019, utils)
#from deeb.datasets import brainInvaders15a, mantegna2019, erpCoreN400, lee2019, utils
#from deeb import paradigms as deeb_paradigms
#from deeb.Evaluation import (CloseSetEvaluation, OpenSetEvaluation,)
from deeb.Evaluation import (WithinSessionEvaluation, CrossSessionEvaluation, 
                             Siamese_WithinSessionEvaluation, Siamese_CrossSessionEvaluation)
log = logging.getLogger(__name__)

def benchmark(subjects=None,
              pipelines="../single_dataset_pipelines/",
              evaluations=None,
              paradigms=None,
              results='./results',
              output="./benchmark/",
              contexts=None,):
    """ Benchmark a set of pipelines on a given paradigm and evaluation"""
    if evaluations is None:
        evaluations = ['Within_Session', 'Cross_Session', 'Siamese_WithinSession', 'Siamese_CrossSession']

    eval_type={'Within_Session':WithinSessionEvaluation,
               'Cross_Session':CrossSessionEvaluation,
               'Siamese_WithinSession':Siamese_WithinSessionEvaluation,
               'Siamese_CrossSession':Siamese_CrossSessionEvaluation}
    
    output = Path(output)
    if not osp.isdir(output):
        os.makedirs(output)

    pipeline_config = parse_pipelines_for_single_dataset(pipelines)
    #print("pipeline_config",pipeline_config[0]['pipeline']['autoregressive'].order)

    context_params = {}
    #print("contexts",contexts)
    if contexts is not None:
        #print("changing context")
        with open(contexts, "r") as cfile:
            context_params = yaml.load(cfile.read(), Loader=yaml.FullLoader)
            #print("context_params",context_params)
    # prdgm = get_paradigm(pipeline_config, context_params, log)

    # print("Paradigms: ", prdgm)
    prdgms = get_paradigm_from_config(pipeline_config, context_params, log)
    print("Paradigms: ", prdgms['pipelines'].keys())
    #print("Paradigms: ", prdgms)
    #if len(context_params) == 0:
        #for paradigm in prdgm:
    context_params["paradigm"] = {}

    #print("Context: ", context_params)
    df_eval = []
    for evaluation in evaluations:
        #print("evaluation",evaluation)
        eval_results = dict()
        #log.debug(f"{paradigm}: {context_params[paradigm]}")
        #dataset=context_params['dataset']
        #print("context_params",context_params.keys())
        dataset=prdgms['dataset']
        #print("dataset",dataset.subject_list)
        #dataset=dataset()
        #dataset.subjects=dataset.subjects[:context_params['dataset']['subjects']]
        # print("type of dataset",type(dataset))
        # print("Instance variable of the dataset", dir(dataset))
        # code=dataset.code
        #dataset.subjects=dataset.subjects[:context_params['dataset']['subjects']]
        
        # if "subects" in pipeline_config[0]['dataset']['parameters']:
        #     dataset.subject_list=dataset.subject_list[:pipeline_config[0]['dataset']['subjects']]
        
        # if "interval" in pipeline_config['dataset']['parameters']:
        #     dataset.interval=pipeline_config[0]['dataset']['interval']

        if dataset.paradigm == "p300":
            #paradigm_300= P300()
            #p = getattr(paradigm_300)(**context_params['paradigm'])
            p=P300()
        else: 
            #paradigm_N400= N400()
            #p = getattr(paradigm_N400)(**context_params['paradigm'])
            p=N400()

        log.debug(context_params['paradigm'])
        ppl_with_epochs, ppl_with_array = {}, {}
        print("evaluation",evaluation.split("_"))
        if (evaluation.split("_")[0]=='Siamese'):
            print("Siamese evaluation")
            if (evaluation=='Siamese_CrossSession') and (dataset.n_sessions<3):
                continue
            else:

                if "siamese" not in prdgms['pipelines'].keys():
                    #print("Please provide siamese pipelines for siamese evaluation")
                    continue
                else:
                    for pn, pv in prdgms['pipelines'].items():
                        if "siamese" in pn:
                            ppl_with_epochs[pn] = pv
                        else:
                            print("Please provide siamese pipelines for siamese evaluation")
                            continue
                    #print("ppl_with_array",ppl_with_array[pn])
                    context = eval_type[evaluation](
                                paradigm=p,
                                datasets=dataset,
                            )
                    
                        # Calling the evualtion function
                    paradigm_results = context.process(
                            pipelines=ppl_with_epochs
                        )
                            
                    df_eval.append(paradigm_results)

        else:
            if (evaluation=='Cross_Session') and (dataset.n_sessions<3):
                continue
            else:

                # if "siamese" in prdgms['pipelines'].keys():
                #     print("Please provide non-siamese pipelines for non-siamese evaluation")
                #     continue
                # else:
                for pn, pv in prdgms['pipelines'].items():
                    if "siamese" in pn:
                       print("Please provide non-siamese pipelines for non-siamese evaluation")
                       continue
                        #print("pn",pn)
                    else:
                        ppl_with_array[pn] = pv
                #print("ppl_with_array",ppl_with_array[pn])

                #print("ppl_with_array")
                context = eval_type[evaluation](
                            paradigm=p,
                            datasets=dataset,
                            # random_state=42,
                            # hdf5_path=results,
                            # n_jobs=1,
                            # return_epochs=True,
                        )
                
                    # Calling the evualtion function
                paradigm_results = context.process(
                        pipelines=ppl_with_array
                    )
                        
                df_eval.append(paradigm_results)


        # if (evaluation=='CrossSession' or evaluation=='SiameseCrossSession') and (dataset.n_sessions==1):
        #     continue
        # else:

        #     for pn, pv in prdgms['pipelines'].items():
        #         if "braindecode" in pn:
        #             ppl_with_epochs[pn] = pv
        #         else:
        #             ppl_with_array[pn] = pv
        #     #print("ppl_with_array",ppl_with_array[pn])
        #     context = eval_type[evaluation](
        #                 paradigm=p,
        #                 datasets=dataset,
        #                 # random_state=42,
        #                 # hdf5_path=results,
        #                 # n_jobs=1,
        #                 # return_epochs=True,
        #             )
                
        #         # Calling the evualtion function
        #     paradigm_results = context.process(
        #             pipelines=ppl_with_array
        #         )
                    
        #     df_eval.append(paradigm_results)

            #df = pd.concat(df_eval)
    return pd.concat(df_eval)

        
        #print("paradigm",paradigm)
        #print("context_params",context_params)
        #print("pipeline_config",pipeline_config)
        #print("evaluation",evaluation)
        #print("eval_type",eval_type)
        #print("output",output)
        #print("results",results)
        #print("subjects",subjects)
        #print("pipeline_config",pipeline_config)
        #print("pipeline_config",pipeline_config)
        #print("pipeline_config",pipeline_config)
        #print("pipeline_config",pipeline_config)
        #print("pipeline_config",pipeline_config)

        
        #p = getattr(deeb_paradigms, paradigm)(**context_params[paradigm])
    

# Creating main function
if __name__ == "__main__":
    # Creating an object

    # Calling function
    #obj.run()
    result=benchmark()
    #print(result.columns)
    result['pipeline']=result['pipeline'].apply(lambda x: x.split('+')[-1])
    grouped_df=result.groupby(['evaluation','pipeline', 'eval Type','dataset']).agg({
                "subject": 'nunique',
                'n_samples': 'first',
                'accuracy': 'mean',
                'auc': 'mean',
                'eer': lambda x: f'{np.mean(x)*100:.3f} ± {np.std(x)*100:.3f}',
                'frr_1_far': lambda x: f'{np.mean(x)*100:.3f}'
            }).reset_index()
    grouped_df.rename(columns={'eval Type':'Scenario', 'subject':'Subjects'}, inplace=True)
    print(grouped_df)



