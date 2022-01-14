/*
 * Copyright (c) 2021 Airbyte, Inc., all rights reserved.
 */

package io.airbyte.integrations.destination.azure_blob_storage.file.uploader;

import com.azure.storage.blob.specialized.AppendBlobClient;
import io.airbyte.integrations.destination.gcs.GcsDestinationConfig;
import io.airbyte.integrations.destination.gcs.jsonl.GcsJsonlWriter;

public class GcsJsonlAzureUploader extends AbstractGcsAzureUploader<GcsJsonlWriter> {

  public GcsJsonlAzureUploader(GcsJsonlWriter writer,
                               GcsDestinationConfig gcsDestinationConfig,
                               AppendBlobClient appendBlobClient,
                               boolean keepFilesInGcs,
                               int headerByteSize) {
    super(writer, gcsDestinationConfig, appendBlobClient, keepFilesInGcs, headerByteSize);
  }

}
