from twitter_clean import launch_twitter_clean
from twitter_util_preprocessing import load_twitter
from twitter_train import exec_train

if __name__ == '__main__':
    # We are going here to launch the first twitter preprocessing
    launch_twitter_clean('social')
    launch_twitter_clean('spatial', 0.5)

    # We are going here to launch the second twitter preprocessing
    load_twitter('social', 128)
    load_twitter('social', 256)
    load_twitter('social', 512)
    load_twitter('social', 768)

    load_twitter('spatial', 128, 0.5)
    load_twitter('spatial', 256, 0.5)
    load_twitter('spatial', 512, 0.5)
    load_twitter('spatial', 768, 0.5)
    
    # We are going here to launch the twitter train and collect the results
    exec_train('social', 128)  
    exec_train('social', 256)
    exec_train('social', 512)
    exec_train('social', 768)

    exec_train('spatial', 128, 0.5)  
    exec_train('spatial', 256, 0.5)
    exec_train('spatial', 512, 0.5)
    exec_train('spatial', 768, 0.5)