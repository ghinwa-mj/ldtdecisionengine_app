#### Tries function calling: Relevant Column is maybe not giving the right column names #### 
#Import required libraries
import os
import streamlit as st
import pandas as pd

from openai import OpenAI
import openai

from google.cloud import storage

# Access secrets directly, no need for json.loads()
gcs_credentials = st.secrets["gcs_service_account"]
openai_api_key = st.secrets["api_keys"]["openai_apikey"]

# Set OpenAI API Key
openai.api_key = openai_api_key

# Initialize Google Cloud Storage client
storage_client = storage.Client.from_service_account_info(gcs_credentials)

# NOTE when running on Digital Ocean, we need to put the credentials somewhere and set the Env GOOGLE_APPLICATION_CREDENTIALS
from google.cloud import storage
import pandas as pd
from io import BytesIO

# Define bucket name
BUCKET_NAME = "wb-ldt"

# Initialize Google Cloud Storage client
storage_client = storage.Client()

def read_csv_from_gcs(bucket_name, file_name):
    """Reads a CSV file from GCS into a Pandas DataFrame."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    data = blob.download_as_bytes()
    return pd.read_csv(BytesIO(data))

# Load CSVs from Google Cloud Storage
df_indicators = read_csv_from_gcs(BUCKET_NAME, "decision_engine/inputs/indicators_full_df.csv")
df_indicatorlist = read_csv_from_gcs(BUCKET_NAME, "decision_engine/inputs/Indicator List.csv")
df_projects = read_csv_from_gcs(BUCKET_NAME, "decision_engine/inputs/wbif_project_examples.csv")

# Extract regions as before
regions = df_indicators['NAME_2'].tolist()

#Update Icon
from PIL import Image
# Loading Image using PIL
import streamlit as st
import base64

from PIL import Image
import requests

def get_image_from_gcs(bucket_name, image_name):
    """Fetch image from GCS and open it."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(image_name)
    image_data = blob.download_as_bytes()
    image = Image.open(BytesIO(image_data))
    return image

# Load the image
im = get_image_from_gcs(BUCKET_NAME, "decision_engine/inputs/LDT Decision Engine Icon.png")

# Set Streamlit page config
st.set_page_config(page_title="LDT Decision Engine", page_icon=im)

# Convert image to base64 - To be able to add to page
def get_base64_from_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Convert and embed the image
icon_html = f'<img src="data:image/png;base64,{get_base64_from_image(im)}" width="30" style="vertical-align: middle; margin-right: 10px;">'


# HTML for inline image in title
icon_html = f'<img src="data:image/png;base64,{get_base64_from_image(im)}" width="30" style="vertical-align: middle; margin-right: 10px;">'
# Display title with icon
st.markdown(f"<h1 style='display: flex; align-items: center;'>{icon_html}LDT Decision Engine</h1>", unsafe_allow_html=True)
# Subheader
st.subheader("Hello, I am your LDT Decision Engine. I can do an automated analysis of regional performances based on the themes you're interested in.")


with st.sidebar:
    st.write("Disclaimer")
    st.markdown(
        """
        <p style="font-size: 0.8rem; color: black;">
            The LDT Decision Engine uses Generative AI functionalities to analyze data, provide regional and project recommendations. 
            While we strive to ensure high-quality and accurate outputs, responses generated by the AI may occasionally contain inaccuracies, outdated information, or unintended biases. 
            Please verify critical information independently.
        </p>
        """,
        unsafe_allow_html=True
    )

# Initialize 'messages' key in session state if not already initialized
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False  

#### List of Regions ####
df_indicators = pd.read_csv("indicators_full_df.csv")
df_indicatorlist = pd.read_csv("Indicator List.csv")
df_projects = pd.read_csv("wbif_project_examples.csv")
regions = df_indicators['NAME_2'].tolist()

#### Create a DataFrame of National Averages ####
averages_df = pd.DataFrame(df_indicators[df_indicators.columns[3:]].mean(), columns=['national_average'])

#Global Variables for the OpenAI Calls
client = OpenAI()
system_message = """You're a data scientist helping regional policy makers make sense of the environmental and economic performance of their regions.
    It is good to perform the performance of each indicator to the national average in order to make logical conclusions. This is what each indicator means.
    Accessibility to Health Services (unit: %): Measures the percentage of citizens with healthcare access within a 60-minute walking distance.
    Accessibility to School Services (unit: %): Measures the percentage of citizens with school access within a 60-minute walking distance.
    Diversity of Health Services: Evaluates healthcare service diversity within a municipality using the Shannon Diversity Index.
    Emissions from all sources (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from all sources.
    Emissions from Coal Power Plants (unit: kgCO2e/kg): Quantifies emissions from coal power plants specifically, aggregating data by emission type.
    Nighttime Luminosity: Measures artificial nighttime light as an economic development indicator using NASA's Black Marble data.
    Key Structure Average Broadband Download Speed (unit: megabites per second): Calculates the average broadband speed for key structures like schools and hospitals.
    Average Cellular Download Speed (unit: megabites per second): Measures average mobile download speeds across sub-national regions.
    Key Structures without Internet Access (unit: %): Shows the percentage of key structures lacking broadband internet access.
    Road flood risk per capita (unit: per capita): Assesses road exposure to 1-in-100-year flood risks per capita for climate adaptation planning. 
    Road heatwave risk per capita (unit: per capita): Measures road length at risk from heatwaves per capita in high-emission climate scenarios.
    Railway flood risk per capita (unit: per capita): Assesses railway exposure to 1-in-100-year flood risks per capita.
    Railway heatwave risk per capita (unit: per capita): Measures railway length at risk from heatwaves per capita in high-emission scenarios.
    Road flood risk (unit: km): Assesses road exposure to 1-in-100-year flood risks for climate adaptation planning. 
    Road heatwave risk (unit: per km): Measures road length at risk from heatwaves in high-emission climate scenarios.
    Railway flood risk (unit: km): Assesses railway exposure to 1-in-100-year flood risks.
    Railway heatwave risk (unit: km): Measures railway length at risk from heatwaves in high-emission scenarios.
    PM 2.5 concentration (unit: µg/m3): Calculates average annual PM 2.5 concentration in sub-national regions, a key health risk factor.
    Agriculture Emissions (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from agriculture sources.
    Forestry & LandUse Emissions (unit: kgCO2e/kg): Quantifies total emissions and emission factors at the municipal level from forestry and land-use sources.
    """

#Create a selectbox with the regions as options
option_region = st.selectbox(
    "Select a region:",
    regions, 
    index = None
)

option_category = st.selectbox(
    "What type of analysis are you interested in?",
    ("Sustainable Transport", "Environment", "Digitalization", "Health", "Education"), 
    index = None
    )

def copy_to_clipboard_button(text):
    st.components.v1.html(
        f"""
        <div>
            <textarea id="copyText" style="display:none;">{text}</textarea>
            <button onclick="copyToClipboard()" 
                style="padding: 8px 16px; background-color: #dfe5f5; color: black; border: none; border-radius: 4px; cursor: pointer;">
                Copy to Clipboard
            </button>
        </div>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById('copyText');
                copyText.style.display = 'block';
                copyText.select();
                document.execCommand('copy');
                copyText.style.display = 'none';
                alert('Text copied to clipboard!');
            }}
        </script>
        """,
        height=50,
    )


tools = [{
    "type": "function",
    "function": {
        "name": "extract_relevant_data",
        "description": "Extract relevant columns from a particular dataset based on the region we are interested in and the columns relevant to the subcategory being analyzed.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Region being analyzed and of which the data needs to be extracted"
                },
                "relevant_columns": {
                    "type": "array",
                    "description": "List of column titles that should be extracted from the dataset because they are relevant to the subcategory we are analyzing",
                    "items": { "type": "string" }  
                }
            },
            "required": ["region"],  
            "additionalProperties": False
        }
    }
}]

def extract_regional_data(df, region, relevant_columns):
    """
    Filters the DataFrame based on the specified region and relevant columns.

    Parameters:
    - df (pd.DataFrame): The dataset containing all regions and indicators.
    - region (str): The region to filter by, matching df["GID_2"].
    - relevant_columns (list): List of column names to keep in the filtered dataset.

    Returns:
    - pd.DataFrame: The filtered DataFrame containing only the specified region and relevant columns.
    """
    # Ensure relevant columns exist in the DataFrame
    valid_columns = ["NAME_2"] + [col for col in relevant_columns if col in df.columns]
    return df.loc[df["NAME_2"] == region, valid_columns]


def extract_national_data(df, relevant_columns):
    df = df.T 
    valid_columns = [col for col in relevant_columns if col in df.columns]

    return df[valid_columns]


st.write("Region selected:", option_region)
st.write("Category selected:", option_category)

def df_indicatorlist_analysis(category_temp, df_temp, region_temp):
    status_temp = f"Starting analysis on {category_temp} in {region_temp}..."
    with st.status(status_temp, expanded=True) as status:
        json_columns = df_temp.to_json(orient='records')
        question_output = f"""From the attached dataframe, which indicators belong to the following subcategory? {category_temp}
            Mention the full name of the indicator (not the column title) in **bold**, followed by ':' and its full description in regular text.
            Ensure the indicators are logically relevant to the category based on the provided information.
            This is the dataframe: {json_columns}"""
        
        
        messages = [
        {"role": "system", "content": system_message},  # System message
        {"role": "user", "content": question_output}]  # User message

        response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=1
            )

    return response.choices[0].message.content

def regional_analysis(region_temp, relevant_indicators):
    status_temp = "Conducting regional analysis..."
    with st.status(status_temp, expanded=True) as status:
        json_columns = df_indicators.columns[3:].tolist()  # Convert to list instead of str

        # Optimized prompt using f-string
        question_output_2 = (
            f"Based on this response: {relevant_indicators}, extract all relevant indicators, column titles, mentioned in this response only for the region of {region_temp}. Ensure all mentioned indicators are extracted to explain the region's performance. The dataset looks like this: {json_columns}."
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": question_output_2}
        ] 

        response_2 = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=1,
            tools=tools,
            tool_choice="auto"
        )

        # Extract tool call results
        tool_calls = response_2.choices[0].message.tool_calls
        relevant_columns = []
        region = None

        for tool in tool_calls:
            if tool.function.name == "extract_relevant_data":
                arguments_dict = json.loads(tool.function.arguments)
                region = arguments_dict.get("region")
                relevant_columns = arguments_dict.get("relevant_columns", [])

        if relevant_columns:
            regional_df = extract_regional_data(df_indicators, region, relevant_columns).to_json(orient='records')
            national_df = extract_national_data(averages_df, relevant_columns).to_json(orient='records')

            print(regional_df)
            print(national_df)

            # Improved comparison prompt
            user_message = (
                f"Compare the regional performance found here to the national average. Make sure to mention all the indicators.\n"
                f"- **Format:** Bullet points with indicators in **bold**.\n"
                f"- Include regional performance, national performance, units, and analysis.\n"
                f"- Use only the indicators from this response, ensuring all are included.\n\n"
                f"Regional Data: {regional_df}\nNational Data: {national_df}\n\n"
                f"Finally, summarize what this means for regional performance."
            )

            messages.append({"role": "user", "content": user_message})

            comparison = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=1
            )

        return comparison.choices[0].message.content

def project_recommendation_agent(region_temp, subcategory, regional_analysis):
    status_temp = f"Doing some background research on {region_temp}... This may take a moment."
    with st.status(status_temp, expanded=True) as status:
        # SYSTEM MESSAGE
        system_message = (
            "You are a researcher helping gather economic, environmental, geographic, and market data. "
            "You will output relevant responses backed by detailed evidence. You will not make things up."
        )

        # FIRST REQUEST - General Regional Summary
        question1 = (
            f"Summarize the relevant information about {region_temp} (region in Serbia). "
            "If the data is available, start with its population, exact location, and most relevant economic markets. "
            "Provide accurate sources (including links) for your information. If you cannot provide relevant data sources "
            "for each point made, simply say no information is available."
        )

        messages = [{"role": "system", "content": system_message}, {"role": "user", "content": question1}]

        response = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=1)
        regional_summary1 = response.choices[0].message.content

        # SECOND REQUEST - Economic, Environmental, and Geographic Structure
        question2 = (
            f"If the data is available, explain {region_temp}'s (region in Serbia) economic, environmental, and "
            "geographic structure, focusing on its assets, weaknesses, and most relevant challenges. "
            "Provide accurate sources (including links) for your information. If you cannot provide relevant data sources, "
            "simply say no information is available."
        )

        messages.append({"role": "user", "content": question2})

        response = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=1)
        regional_summary2 = response.choices[0].message.content

        # THIRD REQUEST - Project Recommendations
        user_message3 = (
        "Your task is to generate project recommendations for the region. However, these recommendations must be "
        "**strictly based on the dataset analysis** and not invented based on general assumptions.\n\n"
        
        "### **Dataset-Based Economic Performance Analysis:**\n"
        f"{regional_analysis}\n\n"

        "### **Regional Context (For Refinement, Not Idea Generation):**\n"
        "The following background information about the region should only be used to refine or adjust the recommendations "
        "from the dataset. It should **not** be used to create recommendations that are not supported by the dataset.\n\n"
        
        "**General Summary:**\n"
        f"{regional_summary1}\n\n"

        "**Economic & Geographic Summary:**\n"
        f"{regional_summary2}\n\n"

        "### **Instructions:**\n"
        "- **Only suggest project recommendations that align directly with the dataset analysis.**\n"
        "- The regional summary should be used **only** to refine or contextualize these recommendations, not to generate new ones.\n"
        "- **Do not introduce recommendations that are not clearly supported by the dataset.**\n"
        "- Justify each recommendation by clearly referencing the dataset-based analysis.\n")
        messages.append({"role": "user", "content": user_message3})

    # SHOW INTERMEDIATE RESPONSE (Processing Message)
    with st.status("Generating project recommendations... This may take a moment.", expanded=True) as status:
        response_3 = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=1)
        initial_recommendations = response_3.choices[0].message.content
        
        # DISPLAY INITIAL RESPONSE
        st.subheader("Initial Project Recommendations")
        st.write(initial_recommendations)

        # FILTER RELEVANT PROJECTS
        df_projects_temp = df_projects[df_projects['Investment Sector'].str.contains(subcategory, case=False, na=False)]
        json_projects = df_projects_temp.to_json(orient="records")

        relevant_projects_q = "Based on these project recommendations:" + str(response_3.choices[0].message.content) + ", filter through the projects in the following dataset and pick the five most relevant ones based on project description, fit and title. The projects should be used as a baseline for policy makers to learn from. Outline the most relevant projects, their project description, where they took place, expexted beneficiares and outlined cost and include the url link to learn about them. If the projects themes are not thematically relevant to the project recommendations, do not include them. This is the dataset: " + str(json_projects)
        messages.append({"role": "user", "content": relevant_projects_q})

        response_4 = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=1)
        final_project_selection = response_4.choices[0].message.content

        # DISPLAY FINAL OUTPUT
        st.subheader("Final Project Selections")
        st.write(final_project_selection)

        # UPDATE STATUS
        status.update(label="Process Completed!", state="complete")

    return initial_recommendations, final_project_selection

# Initialize session state flags if they don’t exist
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'regional_analysis_completed' not in st.session_state:
    st.session_state.regional_analysis_completed = False
if 'project_recommendations_completed' not in st.session_state:
    st.session_state.project_recommendations_completed = False

# First button to start the process
if st.button("Let's get started"):
    if not st.session_state.analysis_completed:
        #st.write("Starting analysis...")
        relevant_indicators = df_indicatorlist_analysis(option_category, df_indicatorlist, option_region) 
        st.session_state.relevant_indicators = relevant_indicators
        #st.session_state.response_list = response_list
        st.session_state.analysis_completed = True  # Set flag to True after first execution

# Display the initial analysis result if it exists in session state
if st.session_state.get("relevant_indicators"):
    st.write(st.session_state.relevant_indicators)
    copy_to_clipboard_button(st.session_state.relevant_indicators)


# Second button only appears after the first analysis is complete
if st.session_state.analysis_completed:
    if st.button("Let's conduct a Regional Analysis") and not st.session_state.regional_analysis_completed:
        #st.write("Conducting Regional Analysis...")
        #indicator_meanings_result = indicator_meanings(df, st.session_state.response_written)
        regional_analysis_results = regional_analysis(option_region, st.session_state.relevant_indicators)
        st.session_state.regional_analysis_results = regional_analysis_results
        st.session_state.regional_analysis_completed = True
        #st.write(regional_analysis_results)

# Display regional analysis if it exists
if st.session_state.get("regional_analysis_results"):
    st.write(st.session_state.regional_analysis_results)
    copy_to_clipboard_button(st.session_state.regional_analysis_results)


if st.session_state.regional_analysis_completed == True:
      # Ensure function only runs once
    if st.button("What Project Recommendations Follow?") and not st.session_state.project_recommendations_completed:
        #st.write("Extracting Relevant Project Recommendations...")
        project_recommendations = project_recommendation_agent(option_region, option_category, st.session_state.regional_analysis_results)
        st.session_state.project_recommendations_completed = True
        st.session_state.project_recommendations = project_recommendations

if st.session_state.get("project_recommendations"):
    #st.write(st.session_state.project_recommendations)
    copy_to_clipboard_button(st.session_state.project_recommendations)



