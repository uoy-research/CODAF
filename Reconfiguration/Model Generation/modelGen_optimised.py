import json
import subprocess
import numpy as np
from scipy.optimize import minimize, NonlinearConstraint

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

def check_properties_with_prism(prism_model_file, properties_file):
    """Run PRISM to check the properties."""
    cmd = f"prism {prism_model_file} {properties_file}"
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.stdout

def parse_prism_output(output):
    """Parse the PRISM output to extract the results of the properties."""
    lines = output.split("\n")
    results = {}
    
    for line in lines:
        if "Result:" in line:
            _, rest_of_line = line.split("Result:", 1)
            value = float(rest_of_line.split(" ")[1])
            if "cost" not in results:
                property_name = "cost"
            elif "delay" not in results:
                property_name = "delay"
            else:
                property_name = "assuranceConfidenceLevel"
            results[property_name] = value
            
    return results

def evaluate_against_targets(prism_results, targets):
    """Evaluate PRISM results against targets and print messages."""
    messages = []
    for property_name, target_value in targets.items():
        actual_value = prism_results.get(property_name, None)
        if actual_value is not None:
            if property_name == "assuranceConfidenceLevel":
                if actual_value >= target_value:
                    messages.append(f"{property_name} is satisfied. Target: {target_value}, Actual: {actual_value}")
                else:
                    messages.append(f"{property_name} is NOT satisfied. Target: {target_value}, Actual: {actual_value}")
            else:
                if actual_value <= target_value:
                    messages.append(f"{property_name} is satisfied. Target: {target_value}, Actual: {actual_value}")
                else:
                    messages.append(f"{property_name} is NOT satisfied. Target: {target_value}, Actual: {actual_value}")
        else:
            messages.append(f"Couldn't find results for {property_name} in PRISM output.")
    
    return messages

def combined_objective_function(decision_variables, config, properties_file):
    """Combines multiple objectives for optimization."""
    adjusted_config = adjust_mdp_parameters(config, decision_variables)
    mdp_model = generate_mdp_model(adjusted_config)
    filename = save_mdp_model_to_file(mdp_model, adjusted_config['reconfigurations'])
    prism_output = check_properties_with_prism(filename, properties_file)
    prism_results = parse_prism_output(prism_output)
    evaluation_messages = evaluate_against_targets(prism_results, adjusted_config['targets'])
    
    # Combine objectives
    cost, delay, assurance = decision_variables
    cost_target, delay_target, assurance_target = adjusted_config['targets'].values()
    
    cost_diff = max(0, cost - cost_target)
    delay_diff = max(0, delay - delay_target)
    assurance_diff = max(0, assurance_target - assurance)
    
    # Adding a penalty for configurations where delay and cost do not have the desired relationship
    # Assuming that higher delay should lead to lower cost
    penalty = np.abs(delay * cost - some_constant)
    
    return cost_diff + delay_diff + assurance_diff + penalty

def constraint(decision_variables):
    """Constraint to ensure that delay and cost are inversely related."""
    cost, delay, _ = decision_variables
    return delay * cost - some_constant

def optimize_mdp_parameters(config, properties_file):
    """Optimizes MDP parameters to satisfy target conditions."""
    bounds = [(0.00001, 10), (0.00001, 10), (0.00001, 10)]  # Avoiding 0 as lower bound
    nonlinear_constraint = NonlinearConstraint(constraint, 0, np.inf)
    result = minimize(combined_objective_function, initial_guess, args=(config, properties_file), bounds=bounds, constraints=[nonlinear_constraint], options={'disp': True})
    
    if result.success:
        optimized_config = adjust_mdp_parameters(config, result.x)
        return optimized_config, result
    else:
        print("Optimization failed:", result.message)
        return None, None

def adjust_mdp_parameters(config, decision_variables):
    cost, delay, assurance = decision_variables
    if cost > 0 and delay > 0 and assurance > 0:
        config['rewards']['cost']['reconfig'][-1] = round(cost, 3)
        config['rewards']['delay']['reconfig'][-1] = round(delay, 3)
        config['rewards']['assuranceConfidenceLevel']['reconfig'][-1] = round(assurance, 3)
        return config
    else:
        print("Invalid reward values:", decision_variables)
        return None

def evaluate_existing_configurations(config, properties_file):
    """Evaluates existing configurations against target conditions."""
    mdp_model = generate_mdp_model(config)
    filename = save_mdp_model_to_file(mdp_model, config['reconfigurations'])
    prism_output = check_properties_with_prism(filename, properties_file)
    prism_results = parse_prism_output(prism_output)
    evaluation_messages = evaluate_against_targets(prism_results, config['targets'])
    print(evaluation_messages)
    all_targets_satisfied = all("not" not in message.lower() for message in evaluation_messages)
    return all_targets_satisfied

def update_configuration(config, properties_file, optimization_failed=False):
    """Updates the MDP configuration based on optimization results or adds a new configuration."""
    if optimization_failed:
        return None, None
    else:
        config['reconfigurations'] += 1
        config['rewards']['cost']['reconfig'].append(0)  # initial value
        config['rewards']['delay']['reconfig'].append(0)  # initial value
        config['rewards']['assuranceConfidenceLevel']['reconfig'].append(0)  # initial value
        
        optimized_config, optimization_result = optimize_mdp_parameters(config, properties_file)
        if optimized_config:
            return optimized_config, optimization_result
        else:
            return update_configuration(config, properties_file, optimization_failed=True)
        
def evaluate_final_solution(config, properties_file, mdp_model):
    # Save the MDP model to a file
    filename = save_mdp_model_to_file(mdp_model, config['reconfigurations'])
    
    # Run PRISM to verify the properties
    prism_output = check_properties_with_prism(filename, properties_file)
    
    # Parse the PRISM output
    prism_results = parse_prism_output(prism_output)
    
    # Compare against target values
    evaluation_messages = evaluate_against_targets(prism_results, config['targets'])
    
    # Print or return the evaluation messages
    for message in evaluation_messages:
        print(message)

if __name__ == '__main__':
    # Define some constant for the relationship constraint
    some_constant = 10 
    
    # Generate initial guesses for the optimization algorithm
    cost_initial_guess = np.random.uniform(0.00001, 10)
    delay_initial_guess = np.random.uniform(0.00001, 10)
    assurance_initial_guess = np.random.uniform(1, 5)
    initial_guess = [cost_initial_guess, delay_initial_guess, assurance_initial_guess]
 
    # Read and parse the configuration file
    config_content = read_config_from_file()
    config = parse_config(config_content)
    
    # Define the path to the PRISM properties file
    properties_file = "./prop.pctl"
    
    # Evaluate the existing configurations
    satisfied = evaluate_existing_configurations(config, properties_file)
    
    # If no existing configuration satisfies the targets, try to find a new configuration
    if not satisfied:
        satisfied, optimization_result = update_configuration(config, properties_file)
    
    # If a satisfying configuration is found, evaluate the final solution
    if satisfied:
        # Generate the MDP model using the updated parameters
        mdp_model = generate_mdp_model(config)
        
        # Evaluate the final solution
        evaluate_final_solution(config, properties_file, mdp_model)
    else:
        print("Could not find a satisfying configuration within the existing configurations.")

