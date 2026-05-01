// Inner module: deploys all workload resources inside the supplied RG.

param location string
param pgAdmin string
@secure()
param pgPassword string
param backendImage string

var prefix = 'sjplanner'
var pgServerName = '${prefix}-pg'
var caEnvName = '${prefix}-cae'
var caAppName = '${prefix}-api'
var laName = '${prefix}-logs'
var aiName = '${prefix}-ai'
var oaiName = '${prefix}-openai'
var kvName = '${prefix}-kv-${uniqueString(resourceGroup().id)}'

resource la 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: laName
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
}

resource ai 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: la.id
    IngestionMode: 'LogAnalytics'
  }
}

resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: pgServerName
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: pgAdmin
    administratorLoginPassword: pgPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource pgDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: pg
  name: 'sjplanner'
}

resource oai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: oaiName
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: oaiName
    publicNetworkAccess: 'Enabled'
  }
}

resource gptDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: oai
  name: 'gpt-4o-mini'
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4o-mini', version: '2024-07-18' }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
  }
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: caEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: la.properties.customerId
        sharedKey: la.listKeys().primarySharedKey
      }
    }
  }
}

resource caApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: caAppName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'auto' }
      secrets: [
        { name: 'pg-pass', value: pgPassword }
        { name: 'oai-key', value: oai.listKeys().key1 }
        { name: 'ai-conn', value: ai.properties.ConnectionString }
        { name: 'jwt-secret', value: uniqueString(resourceGroup().id, 'jwt') }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: backendImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'APP_ENV', value: 'production' }
            { name: 'LOG_JSON', value: 'true' }
            { name: 'DATABASE_URL', value: 'postgresql+psycopg2://${pgAdmin}:${pgPassword}@${pg.properties.fullyQualifiedDomainName}:5432/sjplanner' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: oai.properties.endpoint }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'oai-key' }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: gptDeployment.name }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'ai-conn' }
          ]
          probes: [
            { type: 'Liveness', httpGet: { path: '/api/health', port: 8000 } }
            { type: 'Readiness', httpGet: { path: '/api/health', port: 8000 } }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
}

output backendUrl string = 'https://${caApp.properties.configuration.ingress.fqdn}'
output postgresHost string = pg.properties.fullyQualifiedDomainName
output appInsightsConnection string = ai.properties.ConnectionString
