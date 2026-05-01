// SJ Project Planner Agent — Azure deployment skeleton.
// Resources: Container Apps Environment + Container App (backend),
// Static Web App (frontend), Azure Database for PostgreSQL Flexible Server,
// Azure OpenAI account, Application Insights, Key Vault, Log Analytics.
// Usage:
//   az deployment sub create --location southeastasia \
//     --template-file infra/main.bicep --parameters infra/main.parameters.json

targetScope = 'subscription'

@description('Resource-group name for the deployment')
param rgName string = 'rg-sjplanner-prod'

@description('Azure region')
param location string = 'southeastasia'

@description('Postgres administrator login')
param pgAdmin string = 'sjplanner'

@secure()
@description('Postgres administrator password')
param pgPassword string

@description('Container image for the backend (e.g. ghcr.io/org/sjplanner-api:1.0.0)')
param backendImage string

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
}

module workload 'workload.bicep' = {
  name: 'workload'
  scope: rg
  params: {
    location: location
    pgAdmin: pgAdmin
    pgPassword: pgPassword
    backendImage: backendImage
  }
}

output backendUrl string = workload.outputs.backendUrl
output postgresHost string = workload.outputs.postgresHost
output appInsightsConnection string = workload.outputs.appInsightsConnection
