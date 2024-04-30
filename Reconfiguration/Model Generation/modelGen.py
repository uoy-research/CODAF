import json
import subprocess

def read_config_from_file(filename='config.json'):
    """Reads the configuration file content from a given filename."""
    with open(filename, 'r') as file:
        config_content = file.read()
    return config_content

def parse_config(config_file_content):
    """Parses the configuration file content."""
    config = json.loads(config_file_content)
    return config

def generate_mdp_model(config):
    """Generates the MDP model based on the parsed configuration."""
    
    reconfigs = config['reconfigurations']
    probabilities = config['probabilities']
    
    # Define the states
    states = ['Initialization', 'EnvironmentMonitoring', 'EnvironmentalChangeDetected'] + \
             [f'Reconfiguration{i}' for i in range(1, reconfigs + 1)] + \
             [f'AdjustedOperation{i}' for i in range(1, reconfigs + 1)] + \
             ['BackupOperation', 'NormalOperation', 'MissionCompletion']
    
    # Start the model definition
    model = "mdp\n\nmodule mission\n"
    
    # Add state definitions
    model += "    s : [0..{}] init 0;\n".format(len(states) - 1)
    for idx, state in enumerate(states):
        model += "    // {}: {}\n".format(idx, state)
    
    # Transitions
    model += "\n    [initialize] s=0 -> 1:(s'=1);\n\n"
    model += "    // Monitors the environment and detects changes\n"
    env_change_prob = probabilities['normalOperation']['EnvironmentalChangeDetected']
    mission_comp_prob = probabilities['normalOperation']['MissionCompletion']
    model += "    [detectChanges] s=1 -> {}:(s'={}) + {}:(s'={});\n\n".format(
        env_change_prob, 2, mission_comp_prob, len(states) - 2
    )
    
    for i in range(1, reconfigs + 1):
        model += "    // Transitions from EnvironmentalChangeDetected\n"
        model += "    [chooseReconfig{}] s=2 -> (s'={});\n".format(i, 2 + i)
        reconfig_success_prob = probabilities['reconfigSuccess']
        reconfig_failure_prob = probabilities['reconfigFailure']
        model += "    [reconfig{}] s={} -> {}:(s'={}) + {}:(s'={});\n\n".format(
            i, 2 + i, reconfig_success_prob, 2 + reconfigs + i, reconfig_failure_prob, len(states) - 3
        )
        model += "    // Transitions from AdjustedOperation{}\n".format(i)
        model += "    [AdjustedOperation{}] s={} -> (s'={});\n\n".format(i, 2 + reconfigs + i, len(states) - 1)

    model += "    // Initiating backup operation as reconfiguration failed\n"
    model += "    [backupOperation] s={} -> (s'={});\n\n".format(len(states) - 3, len(states) - 1)
    model += "    // Continuing with normal operation\n"
    model += "    [normalOperation] s={} -> (s'={});\n\n".format(len(states) - 2, len(states) - 1)
    model += "    // Mission completion\n"
    model += "    [completeMission] s={} -> true;\n\n".format(len(states) - 1)
    
    # End the module
    model += "endmodule\n\n"
    
    # Add labels
    model += 'label "missionCompletion" = (s={});\n\n'.format(len(states) - 1)
    
    # Add rewards
    for reward_type, rewards in config['rewards'].items():
        model += '\nrewards "{}"\n'.format(reward_type)
        
        if 'normalOperation' in rewards:
            model += '    [normalOperation] true : {};\n'.format(rewards['normalOperation'])
        
        for i in range(1, reconfigs + 1):
            if 'reconfig' in rewards and i <= len(rewards['reconfig']):
                model += '    [AdjustedOperation{}] true : {};\n'.format(i, rewards['reconfig'][i - 1])
        
        if 'backupOperation' in rewards:
            model += '    [backupOperation] true : {};\n'.format(rewards['backupOperation'])
            
        model += 'endrewards\n'
    
    return model

def save_mdp_model_to_file(mdp_model, reconfigurations):
    """Saves the MDP model to a file with a specified name format."""
    filename = f"model_reconfig_{reconfigurations}.prism"
    with open(filename, 'w') as file:
        file.write(mdp_model)
    return filename

# Function to run PRISM and get its output
def check_properties_with_prism(prism_model_file, properties_file):
    """Run PRISM to check the properties."""
    cmd = f"prism {prism_model_file} {properties_file}"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    
    # Print the PRISM output for diagnostic purposes
    print("----- PRISM Output -----")
    print(result.stdout)
    print("------------------------")
    
    return result.stdout

# Function to parse the PRISM output
def parse_prism_output(output):
    """Parse the PRISM output to extract the results of the properties."""
    lines = output.split("\n")
    results = {}
    
    for line in lines:
        if "Result:" in line:
            # Split the line at "Result:"
            _, rest_of_line = line.split("Result:", 1)
            # Extract the floating-point number
            value = float(rest_of_line.split(" ")[1])
            # Determine the property name based on the order of results
            if "cost" not in results:
                property_name = "cost"
            elif "delay" not in results:
                property_name = "delay"
            else:
                property_name = "assuranceConfidenceLevel"
            results[property_name] = value
            
    return results


# Function to evaluate the results against target values
def evaluate_against_targets(prism_results, targets):
    """Evaluate PRISM results against targets and print messages."""
    messages = []
    for property_name, target_value in targets.items():
        actual_value = prism_results.get(property_name, None)
        if actual_value is not None:
            if property_name == "assuranceConfidenceLevel":  # For max property
                if actual_value >= target_value:
                    messages.append(f"{property_name} is satisfied. Target: {target_value}, Actual: {actual_value}")
                else:
                    messages.append(f"{property_name} is NOT satisfied. Target: {target_value}, Actual: {actual_value}")
            else:  # For min properties
                if actual_value <= target_value:
                    messages.append(f"{property_name} is satisfied. Target: {target_value}, Actual: {actual_value}")
                else:
                    messages.append(f"{property_name} is NOT satisfied. Target: {target_value}, Actual: {actual_value}")
        else:
            messages.append(f"Couldn't find results for {property_name} in PRISM output.")
    
    return messages

# Main execution part 
if __name__ == '__main__':
    config_content = read_config_from_file()
    config = parse_config(config_content)
    mdp_model = generate_mdp_model(config)
    filename = save_mdp_model_to_file(mdp_model, config['reconfigurations'])

    # Check properties using PRISM
    properties_file = "./prop.pctl"
    prism_output = check_properties_with_prism(filename, properties_file)
    prism_results = parse_prism_output(prism_output)
    evaluation_messages = evaluate_against_targets(prism_results, config['targets'])

    # Print the evaluation messages
    for message in evaluation_messages:
        print(message)
