'''
Created on Mar 5, 2018

@author: emigre459
'''
import pandas as pd
from collections import defaultdict


incomplete_reviewers = defaultdict(list)

def import_data(filename):
    '''
    Imports data from EERE eXCHANGE CSV report called 'Review Details Grid.csv' and cleans it up prior to analysis.
    Returns a cleaned dataframe, with 'cleaned' here meaning that incomplete review records are expunged
    and review records with null values for the numeric rating are also removed. Also calculates the weighted
    score for each review criterion and adds a column to the DataFrame called 'Weighted Original Score' to record it.
    
    filename: str. Indicates path relative to location in which this code is used as a module.
    score_range: tuple. Format is (minimum individual score, maximum individual score). Defines the bounds of scores
                    that reviewers could have used.
    '''    
    
    '''
    Assumed header format:
        FOA Number - ignored
        Submission Type - only types expected are 'Concept Paper' or 'Full Application'
        Control Number
        Topic
        Project Title
        Lead Organization
        Reviewer Full Name
        Review Status - only use entries wherein value here is "Completed"
        Rating Title - can be considered synonymous with "Scoring Criterion"
        Weaknesses
        Strengths
        Numeric Rating
        Criteria Weight (as a percentage)
        Average Overall Score for Reviewer - ignored
        Average Overall Score for Submission - ignored
        Weighted Original Score - added by this code
    '''
    
    
    #Note that there is a new row for every review criterion for every reviewer for every project 
        #(so 3 reviewers on project X using 2 review criteria = 3 * 2 = 6 rows)
    df = pd.read_csv(filename, encoding = 'utf-8')
    
    
    #Let's keep a record of which reviewers didn't complete their reviews, and the control numbers of the 
    #reviews in question
        #We'll format as a dict of form {reviewerName: [control1, control2, etc.]}
    
    incomp_df = df[df['Review Status'] != 'Complete']
    gpby = incomp_df.groupby(['Reviewer Full Name', 'Control Number'])
    for name, _ in gpby:
        incomplete_reviewers[name[0]].append(name[1])
        
    #Now that we know who they are, let's get rid of the offending rows to avoid confusion later
    df.drop(incomp_df.index, inplace = True)
    
    #And let's also remove any rows in which the Numeric Rating is null
    df.dropna(subset = ['Numeric Rating'], inplace = True)
    
    df['Weighted Original Score'] = df['Numeric Rating'] * df['Criteria Weight'] / 100
    
    print("These people didn't complete their reviews: \n\t{}".format(incomplete_reviewers))
    
    return df


def reviewer_stats(df):
    '''
    Isolates scores from individual reviewers and returns each reviewer's mean score and standard deviation
    as a tuple of pandas Series in the format (all means, all stdevs)
    
    df: pandas DataFrame. Cleaned df of the format returned by import_data()
    '''
    
    reviewer_scores = df.groupby(['Reviewer Full Name', 'Control Number', 'Topic'])['Weighted Original Score'].sum()
    reviewer_avgs = reviewer_scores.groupby('Reviewer Full Name').mean()
    reviewer_stdevs = reviewer_scores.groupby('Reviewer Full Name').std(ddof=0)
    
    return reviewer_avgs, reviewer_stdevs

def calculate_z(row, reviewer_means, reviewer_stdDevs):
    '''
    Meant to be applied via the apply() method to a DataFrame of the same format as that output by import_data()
    to calculate the z-score for each reviewer's weighted score.
    
    row: DataFrame row. Can have individual column values called by using row[column_name]
    reviewer_means: pandas Series. Index values are unique reviewer names, element values are the average
                    Weighted Scores across all of that reviewers' reviews for this program.
    reviewer_stdDevs: pandas Series. Index values are unique reviewer names, element values are the standard
                    deviations of the Weighted Scores across all of reviewers' reviews for this program.
    '''
    #Assume this will be applied using df.apply(calculate_z, axis=1, args = (reviewer_means, reviewers_stdDevs))
    
    name = row['Reviewer Full Name']
    if reviewer_stdDevs.loc[name] == 0:
        return 0
    else:
        return (row['Weighted Original Score'] - reviewer_means.loc[name]) / reviewer_stdDevs.loc[name]

def normalize_scores(df, score_range):
    '''
    Takes each reviewer's total weighted score for each project, transforms it into a
    z-score, then re-maps it on to a pre-defined normal distribution and returns a new DataFrame
    that is comprised of 5 columns: Reviewer Full Name, Control Number, Weighted Original Score, 
    Weighted Score Z-Score, and Weighted Normalized Score
    
    df: pandas DataFrame. DataFrame of the format returned by import_data()
    reviewerStats: tuple of pandas Series of the format (reviewer means, reviewer standard deviations).
    score_range: tuple of ints of the format (min_score, max_score). Defines the end points of the allowed
                    scoring range.
    '''
    
    '''REMEMBER: z-score correction shouldn't be applied to each criterion's score 
    (which unfortunately was how I used it in the spreadsheet version of this, incorrectly) but rather
    just correct the original weighted score at a project (not criterion) level
    
    z-score = (original_data - mean) / stddev
    normalized_data = z-score * common_stddev + common_mean
    '''
    
    reviewerStats = reviewer_stats(df)
    
    #We'll define the standard deviation of our new common distribution using the definition of a normal
    #distribution as having 99.7% of its data within three standard deviations of the mean.
    
    stddev = (score_range[1] - score_range[0]) / 6
    
    #midpoint of the score range is defined as the mean of the distrib.
    mean = ((score_range[1] - score_range[0]) / 2) + score_range[0]
    
    
    reviewer_scores = df.groupby(['Reviewer Full Name', 'Control Number', 'Topic'])['Weighted Original Score'].sum()
    output_df = pd.DataFrame(reviewer_scores)
    output_df.reset_index(inplace = True)
    #output_df.columns = ['Reviewer Full Name', 'Control Number', 'Topic', 'Weighted Original Score']
    
    output_df['Weighted Score Z-Score'] = output_df.apply(calculate_z, 
                                                          axis=1, 
                                                          args = (reviewerStats[0],
                                                                  reviewerStats[1]))
    
    output_df['Weighted Normalized Score'] = (output_df['Weighted Score Z-Score'] * stddev) + mean
    
    #Let's make sure our new scores don't exceed the bounds of the scoring range
    output_df[output_df['Weighted Normalized Score'] < score_range[0]] = score_range[0]
    output_df[output_df['Weighted Normalized Score'] > score_range[1]] = score_range[1]
    
    return output_df
    
def tab_maker(df):
    '''
    Pulls out Topic names and returns a unique list of 
    Topic + Number entries that can be used as Excel tab/sheet names. Also 
    groups dataframe data by Topic name and returns a list of dataframes. Output
    is a tuple of the form (names, dataframes)
    
    df: pandas DataFrame. DataFrame of the format returned by normalize_scores()
    '''    
    
    #TODO: make this actually work. For now, going to just output to single tab
    
    tab_dfs = []
    
    topNum = df['Topic'].str.split(n=2, expand = True)[1]
    
    for e in topNum:
        temp_df = df.groupby(['Topic', 'Control Number'], 
                             as_index = False)['Weighted Original Score'].mean()
        
                             
        tab_dfs.append(temp_df)
        
    return ("Topic " + topNum).unique()

def summarize_proposals(df):
    '''
    Groups proposals by topic, then by control number/ID, then calculates
    the average (original and normalized) score across reviewers for each
    proposal and returns a dataframe with those averages and standard deviations.
    
    df: pandas DataFrame. DataFrame of the format returned by normalize_scores()
    '''
    
    avg_orig = df.groupby(['Topic', 'Control Number'],
                          as_index = False)['Weighted Original Score'].mean()
    
    avg_norm = df.groupby(['Topic', 'Control Number'],
                          as_index = False)['Weighted Normalized Score'].mean()
                          
    std_orig = df.groupby(['Topic', 'Control Number'])['Weighted Original Score'].std(ddof=0).reset_index()
    
    std_norm = df.groupby(['Topic', 'Control Number'])['Weighted Normalized Score'].std(ddof=0).reset_index()
    
    #Need to make sure the df we use to make our output df has proper column names
    avg_orig.columns = ['Topic', 'Control Number', 'Average Original Score']
    
    summary_df = avg_orig
    summary_df['Original Score StDev'] = std_orig['Weighted Original Score']
    summary_df['Average Normalized Score'] = avg_norm['Weighted Normalized Score']
    summary_df['Normalized Score StDev'] = std_norm['Weighted Normalized Score']
    
    return summary_df

def export_data(df, filename):
    '''
    Exports the results of normalization into a CSV file.
    
    df: pandas DataFrame. DataFrame of the format returned by normalize_scores()
    filename: str. Defines the relative path and filename of the CSV file you want to export to.
    '''
    
    if filename[-5:] != ".xlsx":
        filename = filename[:-4] + ".xlsx"
        
    
    writer = pd.ExcelWriter(filename)
    
    df.to_excel(writer, sheet_name = "Full_Data", 
                freeze_panes = (1,1))
    summarize_proposals(df).to_excel(writer, 
                                     sheet_name = "Summary_Data", 
                                     freeze_panes = (1,1))
    
    #TODO: once you have tab_maker functioning...
    '''
    sheet_names = tab_name_maker(df)
    for name in sheet_names:
        df.to_excel(writer, sheet_name = name, freeze_panes = (1,1))
    
    '''
    
    writer.save()