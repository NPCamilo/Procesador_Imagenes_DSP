export interface DemoData {
  project: {
    title: string;
    course: string;
    source_image: string;
  };
  fase1: {
    sampling: {
      width_px: number;
      height_px: number;
      total_pixels: number;
      spatial_sampling_rate_px: number;
      spatial_nyquist_limit_cycles_per_px: number;
      f_max_spatial_cycles_per_px: number;
      equivalent_1d_sample_rate_hz: number;
      f_max_1d_hz: number;
      nyquist_1d_verdict: string;
    };
    red_filter: {
      num_components: number;
      largest_area_px: number;
      largest_area_percent: number;
      top_5_areas: number[];
    };
  };
  fase2: {
    working_resolution: string;
    stream_4bits: {
      total_bytes: number;
      total_bits: number;
      sqnr_empirical_db: number;
      sqnr_theoretical_db: number;
      first_64_bits: string;
      first_bytes_hex: string;
    };
    compression_lossless: {
      compressed_bytes: number;
      raw_bytes: number;
      ratio: number;
      savings_percent: number;
      psnr_db: number;
    };
    compression_dct: {
      compressed_bytes: number;
      raw_bytes: number;
      ratio: number;
      savings_percent: number;
      psnr_db: number;
    };
  };
  fase3_4_5: {
    tx_manifest: {
      scheme: string;
      sampling_rate_hz: number;
      samples_per_symbol: number;
      compression_ratio: number;
      savings_percent: number;
      compressed_bytes: number;
      crc32_hex: string;
      audio_duration_s: number;
      resolution: [number, number];
    };
    sync_offset_samples: number;
    ber_bfsk: number;
    crc_valid: boolean;
    qam_ber: number;
    image_metrics: {
      psnr_db: number;
      ssim: number;
      pearson_corr: number;
      mse: number;
      compression_ratio: number;
    };
    audio_metrics: {
      snr_db: number;
      pearson_corr: number;
      rmse: number;
    };
  };
  assets: Record<string, string>;
}

export interface LiveTxResponse {
  fase1: {
    sampling: DemoData["fase1"]["sampling"];
    red_filter: {
      num_components: number;
      largest_area_px: number;
      largest_area_percent: number;
    };
    original_png: string;
    red_splash_png: string;
  };
  fase2: {
    nqs_aliased_png: string;
    quantized_png: string;
    digital_stream: {
      bits_per_sample: number;
      total_bits: number;
      total_bytes: number;
      sqnr_empirical_db: number;
      sqnr_theoretical_db: number;
      first_64_bits: string;
      first_bytes_hex: string;
    };
    compression: {
      method: string;
      raw_bytes: number;
      compressed_bytes: number;
      compression_ratio: number;
      savings_percent: number;
      crc32_hex: string;
    };
  };
  fase3_4: {
    manifest: DemoData["fase3_4_5"]["tx_manifest"];
    ber: number | null;
    crc_valid: boolean | null;
    sync_offset_samples: number;
    first_bits: number[];
    rx_bits: number[];
    modulated_zoom: number[];
    spectrum_freqs: number[];
    spectrum_db: number[];
    constellation_iq: [number, number][];
    modulated_wav_url: string;
    demodulated_wav_url: string;
  };
  fase5: {
    source_tx_png: string;
    reconstructed_png: string | null;
    reconstructed_svg: string | null;
    orig_audio_wav_url: string;
    reconstructed_audio_wav_url: string | null;
    metrics: {
      psnr_db: number;
      ssim: number;
      pearson_corr: number;
      mse: number;
      audio_snr_db: number;
      audio_pearson_corr: number;
    } | null;
    dspimg_b64: string;
    peer_zip_b64: string;
  };
}

export interface PeerRxResponse {
  summary: {
    mode: string;
    scheme: string;
    crc_valid: boolean;
    sync_offset_samples: number;
    reconstructed_resolution: [number, number];
  };
  reconstructed_png: string;
  reconstructed_svg: string;
  reconstructed_audio_wav_url: string;
  constellation_iq: [number, number][];
  demodulated_zoom: number[];
}
